"""apps/proposals/views.py — Proposal management API endpoints."""
import json
from django.http import StreamingHttpResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.proposals.models import OrganizationProfile, GrantProposal, ProposalSection
from apps.proposals.serializers import (
    OrganizationProfileSerializer,
    GrantProposalSerializer,
    ProposalSectionSerializer,
    GenerateProposalSerializer,
    RegenerateSectionSerializer,
)
from apps.proposals.tasks import (
    generate_proposal_task,
    regenerate_section_task,
    export_proposal_docx,
)


def get_request_user(request):
    """Fallback to the first user if the request user is anonymous (for local dev)."""
    user = request.user
    if not user or user.is_authenticated is False:
        from django.contrib.auth import get_user_model
        return get_user_model().objects.first()
    return user


# ── Organisation Profile ──────────────────────────────────────────────────────

class OrgProfileListCreate(generics.ListCreateAPIView):
    serializer_class = OrganizationProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
        return OrganizationProfile.objects.filter(owner=user)

    def perform_create(self, serializer):
        user = self.request.user
        if not user or user.is_anonymous:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
        serializer.save(owner=user)


class OrgProfileDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrganizationProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
        return OrganizationProfile.objects.filter(owner=user)


# ── Grant Proposals ───────────────────────────────────────────────────────────

class ProposalListView(generics.ListAPIView):
    """GET /api/proposals/ — list all proposals."""
    serializer_class = GrantProposalSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
        return GrantProposal.objects.filter(
            created_by=user
        ).prefetch_related("sections").select_related("org_profile")


class ProposalDetailView(generics.RetrieveDestroyAPIView):
    """GET/DELETE /api/proposals/{id}/"""
    serializer_class = GrantProposalSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
        return GrantProposal.objects.filter(
            created_by=user
        ).prefetch_related("sections")


@api_view(["POST"])
def generate_proposal(request):
    """
    POST /api/proposals/generate/
    Create a proposal and kick off background generation for all sections.
    """
    ser = GenerateProposalSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data

    user = request.user
    if not user or user.is_anonymous:
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.first()

    # Get org profile
    try:
        org = OrganizationProfile.objects.get(id=d["org_profile_id"], owner=user)
    except OrganizationProfile.DoesNotExist:
        return Response({"error": "Organisation profile not found."}, status=404)

    # Get RFP document if provided
    rfp_doc = None
    if d.get("rfp_document_id"):
        from apps.documents.models import UploadedDocument
        try:
            rfp_doc = UploadedDocument.objects.get(id=d["rfp_document_id"], uploaded_by=user)
        except UploadedDocument.DoesNotExist:
            return Response({"error": "RFP document not found."}, status=404)

    # Create proposal
    proposal = GrantProposal.objects.create(
        created_by   = user,
        org_profile  = org,
        rfp_document = rfp_doc,
        title        = d["title"],
        llm_provider = d["llm_provider"],
        rfp_metadata = {},
    )

    # Create section records
    for sec_data in d["sections"]:
        ProposalSection.objects.create(
            proposal     = proposal,
            name         = sec_data["name"],
            requirements = sec_data.get("requirements", ""),
            page_limit   = sec_data.get("page_limit"),
            order        = sec_data.get("order", 0),
        )

    # Kick off background generation
    generate_proposal_task.delay(str(proposal.id))

    return Response(
        GrantProposalSerializer(proposal).data,
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
def proposal_status(request, pk):
    """GET /api/proposals/{id}/status/ — poll generation status."""
    user = request.user
    if not user or user.is_anonymous:
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.first()

    try:
        proposal = GrantProposal.objects.get(id=pk, created_by=user)
    except GrantProposal.DoesNotExist:
        return Response({"error": "Not found."}, status=404)

    sections = proposal.sections.values("id", "name", "status", "word_count")
    return Response({
        "id":          str(proposal.id),
        "status":      proposal.status,
        "total_words": proposal.total_words,
        "sections":    list(sections),
    })


@api_view(["POST"])
def regenerate_section(request, pk):
    """POST /api/proposals/sections/{id}/regenerate/"""
    ser = RegenerateSectionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    user = request.user
    if not user or user.is_anonymous:
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.first()

    try:
        section = ProposalSection.objects.get(
            id=pk,
            proposal__created_by=user,
        )
    except ProposalSection.DoesNotExist:
        return Response({"error": "Section not found."}, status=404)

    regenerate_section_task.delay(
        section_id        = str(section.id),
        reviewer_feedback = ser.validated_data["reviewer_feedback"],
        provider          = ser.validated_data["llm_provider"],
    )
    return Response({"message": "Regeneration started.", "section_id": str(section.id)})


@api_view(["PATCH"])
def update_section(request, pk):
    """PATCH /api/proposals/sections/{id}/ — save manual edits."""
    user = request.user
    if not user or user.is_anonymous:
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.first()

    try:
        section = ProposalSection.objects.get(
            id=pk, proposal__created_by=user
        )
    except ProposalSection.DoesNotExist:
        return Response({"error": "Section not found."}, status=404)

    serializer = ProposalSectionSerializer(section, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
def export_to_docx(request, pk):
    """POST /api/proposals/{id}/export/ — export proposal to Word doc."""
    user = request.user
    if not user or user.is_anonymous:
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.first()

    try:
        GrantProposal.objects.get(id=pk, created_by=user)
    except GrantProposal.DoesNotExist:
        return Response({"error": "Proposal not found."}, status=404)

    export_proposal_docx.delay(str(pk))
    return Response({"message": "Export started."})


@api_view(["GET"])
def download_docx(request, pk):
    """GET /api/proposals/{id}/download/ — download exported Word doc."""
    from django.http import FileResponse
    user = get_request_user(request)
    try:
        proposal = GrantProposal.objects.get(id=pk, created_by=user)
    except GrantProposal.DoesNotExist:
        return Response({"error": "Not found."}, status=404)

    if not proposal.docx_file:
        return Response({"error": "Export not ready. Run /export/ first."}, status=404)

    return FileResponse(
        proposal.docx_file.open("rb"),
        as_attachment=True,
        filename=f"proposal_{proposal.id}.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@api_view(["PATCH"])
def update_proposal_review(request, pk):
    """PATCH /api/proposals/{id}/review/ — save reviewer notes and status."""
    user = get_request_user(request)
    try:
        proposal = GrantProposal.objects.get(id=pk, created_by=user)
    except GrantProposal.DoesNotExist:
        return Response({"error": "Not found."}, status=404)

    allowed_statuses = [
        GrantProposal.Status.HUMAN_REVIEW,
        GrantProposal.Status.APPROVED,
        GrantProposal.Status.SUBMITTED,
    ]
    new_status = request.data.get("status")
    if new_status and new_status in allowed_statuses:
        proposal.status = new_status

    proposal.reviewer_notes = request.data.get("reviewer_notes", proposal.reviewer_notes)
    proposal.save(update_fields=["status", "reviewer_notes"])
    return Response(GrantProposalSerializer(proposal).data)

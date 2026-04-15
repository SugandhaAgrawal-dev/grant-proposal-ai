"""apps/documents/views.py — Document upload and management endpoints."""
import mimetypes
from pathlib import Path

from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from apps.documents.models import UploadedDocument, ParsedBlock
from apps.documents.serializers import (
    UploadedDocumentSerializer,
    DocumentUploadSerializer,
    ParsedBlockSerializer,
)
from apps.documents.tasks import process_document


def detect_document_type(file) -> str:
    """Detect document type from MIME type."""
    mime = file.content_type or mimetypes.guess_type(file.name)[0] or ""
    if "pdf" in mime:
        return UploadedDocument.DocumentType.PDF
    elif "wordprocessing" in mime or "docx" in mime or "msword" in mime:
        return UploadedDocument.DocumentType.DOCX
    elif "spreadsheet" in mime or "excel" in mime or "xlsx" in mime:
        return UploadedDocument.DocumentType.EXCEL
    elif any(t in mime for t in ["image/png", "image/jpeg", "image/tiff"]):
        return UploadedDocument.DocumentType.IMAGE
    return UploadedDocument.DocumentType.PDF


class DocumentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/documents/          — list all documents for the current user
    POST /api/documents/          — upload a new document
    """
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DocumentUploadSerializer
        return UploadedDocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
        return UploadedDocument.objects.filter(
            uploaded_by=user
        ).prefetch_related("blocks")

    def perform_create(self, serializer):
        user = self.request.user
        if not user or user.is_anonymous:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
        file = self.request.FILES.get("file")
        doc  = serializer.save(
            uploaded_by   = user,
            document_type = detect_document_type(file),
            file_size     = file.size,
            name          = serializer.validated_data.get("name") or file.name,
        )
        # Kick off background parsing
        process_document.delay(str(doc.id))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            UploadedDocumentSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    """
    GET    /api/documents/{id}/   — get document + all parsed blocks
    DELETE /api/documents/{id}/   — delete document
    """
    serializer_class = UploadedDocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
        return UploadedDocument.objects.filter(
            uploaded_by=user
        ).prefetch_related("blocks")


class DocumentBlocksView(generics.ListAPIView):
    """
    GET /api/documents/{id}/blocks/          — all blocks
    GET /api/documents/{id}/blocks/?type=table — filter by block type
    """
    serializer_class = ParsedBlockSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
        doc = UploadedDocument.objects.get(
            id=self.kwargs["pk"],
            uploaded_by=user,
        )
        qs = ParsedBlock.objects.filter(document=doc)
        block_type = self.request.query_params.get("type")
        if block_type:
            qs = qs.filter(block_type=block_type)
        return qs


@api_view(["POST"])
def reprocess_document(request, pk):
    """POST /api/documents/{id}/reprocess/ — re-trigger parsing."""
    try:
        doc = UploadedDocument.objects.get(id=pk, uploaded_by=request.user)
        doc.status = UploadedDocument.Status.UPLOADED
        doc.save(update_fields=["status"])
        process_document.delay(str(doc.id))
        return Response({"message": "Reprocessing started.", "document_id": str(doc.id)})
    except UploadedDocument.DoesNotExist:
        return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

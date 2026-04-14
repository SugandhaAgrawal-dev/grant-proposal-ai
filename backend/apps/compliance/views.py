"""apps/compliance/views.py — Compliance check endpoints."""
import asyncio
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from apps.proposals.models import GrantProposal
from apps.compliance.checker import ComplianceChecker


@api_view(["POST"])
def run_compliance_check(request, proposal_id):
    """
    POST /api/compliance/{proposal_id}/check/
    Run full compliance check on a proposal and return the report.
    """
    try:
        proposal = GrantProposal.objects.prefetch_related("sections").get(
            id=proposal_id, created_by=request.user
        )
    except GrantProposal.DoesNotExist:
        return Response({"error": "Proposal not found."}, status=404)

    checker = ComplianceChecker()
    report  = asyncio.run(checker.check(proposal))

    # Save report to proposal
    proposal.rfp_metadata["compliance_report"] = report.to_dict()
    proposal.save(update_fields=["rfp_metadata"])

    if report.passed:
        proposal.status = GrantProposal.Status.HUMAN_REVIEW
        proposal.save(update_fields=["status"])

    return Response(report.to_dict())


@api_view(["GET"])
def get_compliance_report(request, proposal_id):
    """GET /api/compliance/{proposal_id}/report/ — get last compliance report."""
    try:
        proposal = GrantProposal.objects.get(id=proposal_id, created_by=request.user)
    except GrantProposal.DoesNotExist:
        return Response({"error": "Not found."}, status=404)

    report = proposal.rfp_metadata.get("compliance_report")
    if not report:
        return Response({"error": "No compliance report found. Run /check/ first."}, status=404)

    return Response(report)

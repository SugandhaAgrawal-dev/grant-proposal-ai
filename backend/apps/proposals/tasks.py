"""apps/proposals/tasks.py — Background proposal generation tasks."""
import asyncio
from celery import shared_task


@shared_task(bind=True, max_retries=2, time_limit=3600)
def generate_proposal_task(self, proposal_id: str):
    """Generate all sections of a proposal in the background."""
    from apps.proposals.models import GrantProposal
    from apps.proposals.generator import ProposalGenerator

    try:
        proposal    = GrantProposal.objects.select_related("org_profile").get(id=proposal_id)
        org_profile = proposal.org_profile.to_dict() if proposal.org_profile else {}
        generator   = ProposalGenerator(provider=proposal.llm_provider)
        asyncio.run(generator.generate_full_proposal(proposal, org_profile))
        return {"status": "success", "proposal_id": proposal_id}
    except GrantProposal.DoesNotExist:
        return {"status": "error", "message": f"Proposal {proposal_id} not found"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=2)
def regenerate_section_task(self, section_id: str, reviewer_feedback: str, provider: str = "ollama"):
    """Regenerate one section with reviewer feedback."""
    from apps.proposals.models import ProposalSection
    from apps.proposals.generator import ProposalGenerator

    try:
        section     = ProposalSection.objects.select_related("proposal__org_profile").get(id=section_id)
        org_profile = section.proposal.org_profile.to_dict() if section.proposal.org_profile else {}
        generator   = ProposalGenerator(provider=provider)
        asyncio.run(generator.regenerate_section(section, org_profile, reviewer_feedback))
        return {"status": "success", "section_id": section_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@shared_task
def export_proposal_docx(proposal_id: str):
    """Export a completed proposal to a formatted Word document."""
    from apps.proposals.models import GrantProposal
    from apps.proposals.exporter import ProposalExporter

    proposal = GrantProposal.objects.prefetch_related("sections").get(id=proposal_id)
    exporter = ProposalExporter()
    exporter.export(proposal)
    return {"status": "success", "proposal_id": proposal_id}

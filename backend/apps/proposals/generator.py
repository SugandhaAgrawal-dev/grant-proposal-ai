"""
apps/proposals/generator.py

Healthcare Grant Proposal Generator
=====================================
Generates each proposal section using the multi-LLM router.
Supports: blocking, streaming, regeneration with feedback, full proposal.
"""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from apps.llm.router import LLMRouter
from apps.proposals.models import GrantProposal, ProposalSection


BASE_SYSTEM_PROMPT = """You are a senior healthcare grant writer with 20+ years of experience
writing winning proposals for Federally Qualified Health Centers (FQHCs), hospital systems,
community health organisations, and managed care networks responding to CMS, HHS/HRSA,
state Medicaid, SAMHSA, and private foundation grants.

Your writing is:
1. EVIDENCE-BASED: Ground every claim in specific data — patient volumes, outcome percentages,
   contract values, years of operation.
2. COMPLIANCE-AWARE: Address HIPAA, 42 CFR Part 2, and any regulatory requirements proactively.
3. PATIENT-CENTRED: Connect every element to impact on the communities served.
4. REQUIREMENT-ALIGNED: Map your response to the evaluation criteria weights.
5. HONEST: Never fabricate statistics, client names, or certifications.
6. STRUCTURED: Use ## headings, ### sub-headings, bullet points for lists.

Hard rules:
- Never include [TBD] or [INSERT] placeholders
- Write in active voice
- Start content directly — no preambles like "Here is the section..."
"""

SECTION_ADDENDUMS = {
    "technical": (
        "Structure with clear sub-headings for each methodology component. "
        "Include approach overview, activities, tools, timeline, and measurable outputs."
    ),
    "management": (
        "Include organisational structure, roles, governance model, "
        "communication plan, and escalation procedures."
    ),
    "past_performance": (
        "Format each example: Agency → Contract Value → Period → Scope → Your Role → Outcomes. "
        "Include at least 2–3 quantified outcome metrics per example."
    ),
    "staffing": (
        "Include a staffing table: Role | FTE | Qualifications | Experience. "
        "Add a brief bio for each key person."
    ),
    "budget": (
        "Present line items: Personnel | Fringe | Travel | Equipment | Supplies | Indirect. "
        "Justify every line item. Ensure costs align with the proposed scope."
    ),
    "executive_summary": (
        "Open with the community need. Summarise the solution in 2 sentences. "
        "Highlight 3 strongest differentiators. Close with a commitment statement."
    ),
    "data_security": (
        "Address: HIPAA Privacy Rule, HIPAA Security Rule, AES-256 encryption, "
        "TLS 1.3, BAA, role-based access, audit logging, HITRUST/SOC 2."
    ),
}

STRATEGY_MAP = {
    "technical approach":  "technical",
    "methodology":         "technical",
    "management plan":     "management",
    "past performance":    "past_performance",
    "relevant experience": "past_performance",
    "staffing plan":       "staffing",
    "key personnel":       "staffing",
    "budget":              "budget",
    "cost":                "budget",
    "executive summary":   "executive_summary",
    "data security":       "data_security",
    "hipaa":               "data_security",
    "privacy":             "data_security",
}


def detect_strategy(section_name: str) -> str:
    name = section_name.lower()
    for keyword, strategy in STRATEGY_MAP.items():
        if keyword in name:
            return strategy
    return "default"


def build_system_prompt(strategy: str) -> str:
    addendum = SECTION_ADDENDUMS.get(strategy, "Use clear headings, be specific and evidence-based.")
    return f"{BASE_SYSTEM_PROMPT}\n\n## For this section:\n{addendum}"


def build_section_prompt(
    section_name:        str,
    requirements:        str,
    org_profile:         dict,
    evaluation_criteria: list[dict] | None = None,
    page_limit:          int | None = None,
    reviewer_feedback:   str | None = None,
    previous_draft:      str | None = None,
) -> str:
    certs = ", ".join(org_profile.get("certifications") or ["HIPAA"])

    org_block = (
        "## Organisation profile\n"
        f"- **Name**: {org_profile.get('name', 'Our Organisation')}\n"
        f"- **Service area**: {org_profile.get('service_area', 'Not specified')}\n"
        f"- **Patient population**: {org_profile.get('patient_population', 'Not specified')}\n"
        f"- **Annual volume**: {org_profile.get('annual_patient_volume', 'Not specified')}\n"
        f"- **Certifications**: {certs}\n"
        f"- **Mission**: {org_profile.get('mission_statement', '')}"
    )

    page_note = f"\n> **Page limit**: {page_limit} pages (~{page_limit * 275} words)" if page_limit else ""

    req_block = f"## RFP requirements — {section_name}\n{requirements}{page_note}"

    criteria_block = ""
    if evaluation_criteria:
        lines = "\n".join(f"  - {c['criterion']}: **{c['weight']}%**" for c in evaluation_criteria)
        criteria_block = f"## Evaluation criteria\n{lines}"

    feedback_block = ""
    if reviewer_feedback:
        feedback_block = f"## Reviewer feedback — incorporate this\n{reviewer_feedback}"

    prev_block = ""
    if previous_draft:
        prev_block = f"## Previous draft (revise based on feedback)\n{previous_draft[:800]}..."

    instruction = (
        "---\n\n"
        f'Write the complete **"{section_name}"** section now.\n'
        "- Use ## and ### markdown headings\n"
        "- Address every sub-requirement\n"
        "- Bold key metrics and certifications\n"
        "- Do NOT add a preamble — start writing directly"
    )

    parts = [org_block, req_block, criteria_block, feedback_block, prev_block, instruction]
    return "\n\n".join(p for p in parts if p.strip())


class ProposalGenerator:
    """
    Generates healthcare grant proposal sections using the LLM router.

    Usage:
        gen = ProposalGenerator(provider="ollama")   # or "openai" / "claude"

        # Generate one section
        content, time_s = await gen.generate_section(section, org_profile)

        # Stream one section
        async for token in gen.stream_section(section, org_profile):
            print(token, end="")

        # Generate full proposal
        await gen.generate_full_proposal(proposal)
    """

    def __init__(self, provider: str = "ollama"):
        self.provider = provider
        self.router   = LLMRouter(provider=provider)

    async def generate_section(
        self,
        section:             ProposalSection,
        org_profile:         dict,
        evaluation_criteria: list[dict] | None = None,
        temperature:         float             = 0.35,
        max_tokens:          int               = 3500,
    ) -> tuple[str, float]:
        """
        Generate one section. Returns (content, generation_time_seconds).
        Updates the section DB record on completion.
        """
        strategy = detect_strategy(section.name)
        system   = build_system_prompt(strategy)
        prompt   = build_section_prompt(
            section_name        = section.name,
            requirements        = section.requirements,
            org_profile         = org_profile,
            evaluation_criteria = evaluation_criteria,
            page_limit          = section.page_limit,
        )

        section.status = ProposalSection.SectionStatus.GENERATING
        section.save(update_fields=["status"])

        start = time.monotonic()
        try:
            content = await self.router.chat(
                messages    = [{"role": "user", "content": prompt}],
                system      = system,
                temperature = temperature,
                max_tokens  = max_tokens,
            )
            content  = self._clean(content, section.name)
            elapsed  = round(time.monotonic() - start, 2)

            section.content         = content
            section.status          = ProposalSection.SectionStatus.DONE
            section.llm_provider    = self.provider
            section.generation_time = elapsed
            section.save(update_fields=["content", "status", "llm_provider",
                                         "generation_time", "word_count"])
            return content, elapsed

        except Exception as exc:
            section.status = ProposalSection.SectionStatus.FAILED
            section.save(update_fields=["status"])
            raise

    async def stream_section(
        self,
        section:     ProposalSection,
        org_profile: dict,
        evaluation_criteria: list[dict] | None = None,
        temperature: float = 0.35,
        max_tokens:  int   = 3500,
    ) -> AsyncIterator[str]:
        """Stream tokens for a section — use with SSE endpoint."""
        strategy = detect_strategy(section.name)
        system   = build_system_prompt(strategy)
        prompt   = build_section_prompt(
            section_name        = section.name,
            requirements        = section.requirements,
            org_profile         = org_profile,
            evaluation_criteria = evaluation_criteria,
            page_limit          = section.page_limit,
        )

        async for token in self.router.stream(
            messages    = [{"role": "user", "content": prompt}],
            system      = system,
            temperature = temperature,
            max_tokens  = max_tokens,
        ):
            yield token

    async def regenerate_section(
        self,
        section:           ProposalSection,
        org_profile:       dict,
        reviewer_feedback: str,
        temperature:       float = 0.3,
    ) -> tuple[str, float]:
        """Regenerate a section incorporating reviewer feedback."""
        strategy = detect_strategy(section.name)
        system   = build_system_prompt(strategy)
        prompt   = build_section_prompt(
            section_name      = section.name,
            requirements      = section.requirements,
            org_profile       = org_profile,
            reviewer_feedback = reviewer_feedback,
            previous_draft    = section.content,
        )

        start = time.monotonic()
        content = await self.router.chat(
            messages    = [{"role": "user", "content": prompt}],
            system      = system,
            temperature = temperature,
            max_tokens  = 3500,
        )
        elapsed = round(time.monotonic() - start, 2)
        content = self._clean(content, section.name)

        section.content         = content
        section.llm_provider    = self.provider
        section.generation_time = elapsed
        section.save(update_fields=["content", "llm_provider", "generation_time", "word_count"])
        return content, elapsed

    async def generate_executive_summary(
        self,
        proposal:    GrantProposal,
        org_profile: dict,
        temperature: float = 0.4,
    ) -> str:
        """Generate executive summary after all sections are complete."""
        sections_preview = "\n\n".join(
            f"### {s.name}\n{s.content[:400]}..."
            for s in proposal.sections.exclude(name="Executive Summary")[:5]
        )
        meta = proposal.rfp_metadata or {}
        prompt = (
            "Write a compelling **Executive Summary** for this healthcare grant proposal.\n\n"
            f"## Grant context\n"
            f"- Title: {proposal.title}\n"
            f"- Agency: {meta.get('agency', 'Not specified')}\n"
            f"- Deadline: {meta.get('deadline', 'Not specified')}\n\n"
            f"## Organisation\n- Name: {org_profile.get('name')}\n"
            f"- Mission: {org_profile.get('mission_statement', '')}\n\n"
            f"## Section highlights\n{sections_preview}\n\n"
            "Write a 350–500 word Executive Summary:\n"
            "1. Community health need (1 paragraph)\n"
            "2. Proposed solution and unique approach\n"
            "3. Top 3 qualifications with evidence\n"
            "4. Measurable outcomes commitment\n"
            "5. Closing commitment statement\n\n"
            "Begin writing directly — no preamble."
        )
        return await self.router.chat(
            messages    = [{"role": "user", "content": prompt}],
            system      = build_system_prompt("executive_summary"),
            temperature = temperature,
            max_tokens  = 900,
        )

    async def generate_full_proposal(
        self,
        proposal:    GrantProposal,
        org_profile: dict,
        temperature: float = 0.35,
    ) -> None:
        """Generate all sections sequentially and update the proposal status."""
        proposal.status = GrantProposal.Status.GENERATING
        proposal.save(update_fields=["status"])

        try:
            criteria = proposal.rfp_metadata.get("evaluation_criteria", [])
            for section in proposal.sections.exclude(name="Executive Summary"):
                await self.generate_section(
                    section             = section,
                    org_profile         = org_profile,
                    evaluation_criteria = criteria,
                    temperature         = temperature,
                )
                await asyncio.sleep(0.3)    # breathing room for local models

            # Executive summary last
            exec_section = proposal.sections.filter(name="Executive Summary").first()
            if exec_section:
                summary = await self.generate_executive_summary(proposal, org_profile)
                exec_section.content      = summary
                exec_section.status       = ProposalSection.SectionStatus.DONE
                exec_section.llm_provider = self.provider
                exec_section.save(update_fields=["content", "status", "llm_provider", "word_count"])

            proposal.status = GrantProposal.Status.COMPLIANCE_REVIEW
            proposal.save(update_fields=["status"])

        except Exception as exc:
            proposal.status        = GrantProposal.Status.ERROR
            proposal.error_message = str(exc)
            proposal.save(update_fields=["status", "error_message"])
            raise

    def _clean(self, content: str, section_name: str) -> str:
        """Strip LLM preambles and normalise whitespace."""
        patterns = [
            rf"^Here is (?:the )?['\"]?{re.escape(section_name)}['\"]? section[:\s]*\n+",
            r"^(?:Sure|Certainly|Of course)[!,.]?\s+(?:here|below)[^:]*:\s*\n+",
            r"^I(?:'ll| will) (?:now )?write[^:]*:\s*\n+",
        ]
        for p in patterns:
            content = re.sub(p, "", content, flags=re.IGNORECASE | re.MULTILINE)
        content = re.sub(r"\n{4,}", "\n\n\n", content)
        return content.strip()

"""
apps/compliance/checker.py

Compliance Checker
==================
Validates generated proposal sections against:
  1. HIPAA language — PHI mentioned but HIPAA not addressed
  2. Page/word limits — section exceeds allowed length
  3. Required certifications — certs required by RFP not mentioned
  4. LLM deep check — fabrication detection + missing requirements
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional

from apps.proposals.models import GrantProposal, ProposalSection


WORDS_PER_PAGE = 275

HEALTH_CERTS = [
    "HIPAA", "HITRUST", "SOC 2", "Joint Commission",
    "FedRAMP", "ISO 27001", "NCQA", "URAC",
]

PHI_KEYWORDS   = ["patient data", "medical record", "health information", "phi ", "ehr", "emr"]
HIPAA_KEYWORDS = ["hipaa", "privacy rule", "security rule", "business associate", "baa"]


@dataclass
class ComplianceIssue:
    section:    str
    issue_type: str        # hipaa | page_limit | missing_cert | fabrication | missing_req
    severity:   str        # error | warning
    message:    str
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "section":    self.section,
            "issue_type": self.issue_type,
            "severity":   self.severity,
            "message":    self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ComplianceReport:
    passed:   bool
    errors:   int = 0
    warnings: int = 0
    summary:  str = ""
    issues:   list[ComplianceIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed":   self.passed,
            "errors":   self.errors,
            "warnings": self.warnings,
            "summary":  self.summary,
            "issues":   [i.to_dict() for i in self.issues],
        }


class ComplianceChecker:
    """
    Run all compliance checks on a proposal's sections.

    Usage:
        checker = ComplianceChecker()
        report  = await checker.check(proposal)
        print(report.to_dict())
    """

    async def check(self, proposal: GrantProposal) -> ComplianceReport:
        issues: list[ComplianceIssue] = []
        sections  = {s.name: s for s in proposal.sections.all()}
        rfp_meta  = proposal.rfp_metadata or {}
        req_certs = rfp_meta.get("certifications_required", [])
        page_limit= rfp_meta.get("page_limit")

        for sec_name, section in sections.items():
            content = section.content or ""
            issues += self._check_hipaa(sec_name, content)
            issues += self._check_page_limit(sec_name, content, section.page_limit, page_limit)
            issues += self._check_certifications(sec_name, content, req_certs)

        # LLM deep check
        llm_issues = await self._llm_deep_check(sections, rfp_meta)
        issues += llm_issues

        errors   = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")
        passed   = errors == 0

        return ComplianceReport(
            passed   = passed,
            errors   = errors,
            warnings = warnings,
            summary  = (
                f"Compliance check complete. {errors} error(s), {warnings} warning(s). "
                f"{'Ready for human review.' if passed else 'Resolve errors before submission.'}"
            ),
            issues   = issues,
        )

    # ── Rule-based checks ─────────────────────────────────────────────────────

    def _check_hipaa(self, section_name: str, content: str) -> list[ComplianceIssue]:
        cl = content.lower()
        mentions_phi   = any(kw in cl for kw in PHI_KEYWORDS)
        mentions_hipaa = any(kw in cl for kw in HIPAA_KEYWORDS)
        if mentions_phi and not mentions_hipaa:
            return [ComplianceIssue(
                section    = section_name,
                issue_type = "hipaa",
                severity   = "error",
                message    = "Section references patient/PHI data but does not explicitly address HIPAA compliance.",
                suggestion = "Add a sentence confirming HIPAA compliance and BAA availability.",
            )]
        return []

    def _check_page_limit(
        self,
        section_name:  str,
        content:       str,
        section_limit: Optional[int],
        global_limit:  Optional[int],
    ) -> list[ComplianceIssue]:
        word_count = len(content.split())
        if section_limit:
            max_words = section_limit * WORDS_PER_PAGE
            if word_count > max_words:
                return [ComplianceIssue(
                    section    = section_name,
                    issue_type = "page_limit",
                    severity   = "error",
                    message    = f"Section exceeds limit: {word_count} words, max {max_words} ({section_limit} pages).",
                    suggestion = f"Reduce by approximately {word_count - max_words} words.",
                )]
        return []

    def _check_certifications(
        self,
        section_name: str,
        content:      str,
        required_certs: list[str],
    ) -> list[ComplianceIssue]:
        issues = []
        cl = content.lower()
        for cert in required_certs:
            if cert.lower() not in cl:
                if any(kw in section_name.lower() for kw in ["technical", "security", "data", "privacy"]):
                    issues.append(ComplianceIssue(
                        section    = section_name,
                        issue_type = "missing_cert",
                        severity   = "warning",
                        message    = f"Required certification not mentioned: {cert}",
                        suggestion = f"Add a paragraph addressing {cert} compliance.",
                    ))
        return issues

    # ── LLM deep check ────────────────────────────────────────────────────────

    async def _llm_deep_check(
        self,
        sections: dict[str, ProposalSection],
        rfp_meta: dict,
    ) -> list[ComplianceIssue]:
        from apps.llm.router import LLMRouter
        issues: list[ComplianceIssue] = []

        preview = "\n\n".join(
            f"=== {name} ===\n{sec.content[:800]}"
            for name, sec in list(sections.items())[:4]
            if sec.content
        )
        req_summary = "\n".join(
            f"• {s}: {sections[s].requirements[:150]}"
            for s in list(sections.keys())[:5]
            if s in sections and sections[s].requirements
        )

        prompt = f"""You are a compliance reviewer for healthcare grant proposals.

Review these proposal section drafts and identify:
1. Any statistics or claims that appear fabricated or unverifiable
2. Any RFP requirements that appear to be missing or unaddressed

RFP Requirements:
{req_summary}

Proposal sections (first 800 chars each):
{preview}

Return ONLY a JSON array of issues. Each item:
{{"section":"Section Name","issue_type":"fabrication|missing_req","severity":"error|warning","message":"description","suggestion":"fix"}}

If no issues found, return: []

JSON:"""

        try:
            router = LLMRouter()
            raw    = await router.chat(
                messages    = [{"role": "user", "content": prompt}],
                temperature = 0.1,
                max_tokens  = 800,
            )
            import json
            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            data  = json.loads(clean)
            for item in data:
                issues.append(ComplianceIssue(
                    section    = item.get("section", "Unknown"),
                    issue_type = item.get("issue_type", "other"),
                    severity   = item.get("severity", "warning"),
                    message    = item.get("message", ""),
                    suggestion = item.get("suggestion"),
                ))
        except Exception:
            pass

        return issues

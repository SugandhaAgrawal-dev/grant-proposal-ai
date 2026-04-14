"""
apps/llm/tests/test_router.py
Unit tests for the multi-LLM router.
All provider HTTP calls are mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from django.test import TestCase, override_settings


LLM_CONFIG_OLLAMA = {
    "default_provider": "ollama",
    "ollama": {
        "base_url":    "http://localhost:11434",
        "llm_model":   "llama3.1:8b",
        "embed_model": "nomic-embed-text",
        "timeout":     30,
    },
    "openai": {"api_key": "", "model": "gpt-4o"},
    "claude": {"api_key": "", "model": "claude-opus-4-5"},
}


@override_settings(LLM_CONFIG=LLM_CONFIG_OLLAMA)
class TestLLMRouter(TestCase):

    def test_router_defaults_to_ollama(self):
        from apps.llm.router import LLMRouter
        router = LLMRouter()
        self.assertEqual(router.provider, "ollama")

    def test_router_accepts_provider_override(self):
        from apps.llm.router import LLMRouter
        router = LLMRouter(provider="ollama")
        self.assertEqual(router.provider, "ollama")

    def test_router_raises_on_unknown_provider(self):
        from apps.llm.router import LLMRouter
        with self.assertRaises(ValueError):
            LLMRouter(provider="unknown_provider")

    def test_available_providers(self):
        from apps.llm.router import LLMRouter
        providers = LLMRouter.available_providers()
        self.assertIn("ollama", providers)
        self.assertIn("openai", providers)
        self.assertIn("claude", providers)


@override_settings(LLM_CONFIG=LLM_CONFIG_OLLAMA)
class TestOllamaProvider(TestCase):

    def _make_provider(self):
        from apps.llm.providers.ollama import OllamaProvider
        return OllamaProvider(LLM_CONFIG_OLLAMA["ollama"])

    @pytest.mark.asyncio
    async def test_chat_returns_string(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": "HIPAA protects patient health information."},
            "eval_count": 12,
        }
        with patch.object(provider._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.chat(
                messages=[{"role": "user", "content": "What is HIPAA?"}]
            )
        self.assertIsInstance(result, str)
        self.assertIn("HIPAA", result)

    @pytest.mark.asyncio
    async def test_embed_returns_vector(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"embedding": [0.1] * 768}
        with patch.object(provider._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.embed("HIPAA compliance")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 768)

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        provider = self._make_provider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "models": [{"name": "llama3.1:8b"}, {"name": "nomic-embed-text"}]
        }
        with patch.object(provider._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            result = await provider.health_check()
        self.assertEqual(result["status"], "healthy")
        self.assertTrue(result["llm_available"])
        self.assertTrue(result["embed_available"])

    @pytest.mark.asyncio
    async def test_health_check_unavailable_on_error(self):
        provider = self._make_provider()
        with patch.object(provider._client, "get", new_callable=AsyncMock,
                          side_effect=Exception("Connection refused")):
            result = await provider.health_check()
        self.assertEqual(result["status"], "unavailable")


@override_settings(LLM_CONFIG=LLM_CONFIG_OLLAMA)
class TestProposalGenerator(TestCase):

    def _make_generator(self):
        from apps.proposals.generator import ProposalGenerator
        gen = ProposalGenerator(provider="ollama")
        gen.router._provider._client = MagicMock()
        return gen

    @pytest.mark.asyncio
    async def test_detect_strategy_technical(self):
        from apps.proposals.generator import detect_strategy, SectionStrategy
        self.assertEqual(detect_strategy("Technical Approach"), "technical")
        self.assertEqual(detect_strategy("Methodology"),        "technical")

    @pytest.mark.asyncio
    async def test_detect_strategy_past_perf(self):
        from apps.proposals.generator import detect_strategy
        self.assertEqual(detect_strategy("Past Performance"),   "past_performance")
        self.assertEqual(detect_strategy("Relevant Experience"),"past_performance")

    @pytest.mark.asyncio
    async def test_detect_strategy_data_security(self):
        from apps.proposals.generator import detect_strategy
        self.assertEqual(detect_strategy("Data Security Plan"), "data_security")
        self.assertEqual(detect_strategy("HIPAA Compliance"),   "data_security")

    @pytest.mark.asyncio
    async def test_detect_strategy_default(self):
        from apps.proposals.generator import detect_strategy
        self.assertEqual(detect_strategy("Unknown Section XYZ"), "default")

    @pytest.mark.asyncio
    async def test_build_section_prompt_contains_org_name(self):
        from apps.proposals.generator import build_section_prompt
        prompt = build_section_prompt(
            section_name="Technical Approach",
            requirements="Describe your methodology.",
            org_profile={"name": "Valley Health System", "certifications": ["HIPAA"]},
        )
        self.assertIn("Valley Health System", prompt)

    @pytest.mark.asyncio
    async def test_build_section_prompt_contains_requirements(self):
        from apps.proposals.generator import build_section_prompt
        prompt = build_section_prompt(
            section_name="Technical Approach",
            requirements="Describe your unique HIPAA-compliant methodology.",
            org_profile={"name": "Test Org"},
        )
        self.assertIn("HIPAA-compliant methodology", prompt)

    @pytest.mark.asyncio
    async def test_build_section_prompt_contains_page_limit(self):
        from apps.proposals.generator import build_section_prompt
        prompt = build_section_prompt(
            section_name="Technical Approach",
            requirements="Describe your methodology.",
            org_profile={"name": "Test Org"},
            page_limit=10,
        )
        self.assertIn("10 pages", prompt)

    @pytest.mark.asyncio
    async def test_build_section_prompt_contains_reviewer_feedback(self):
        from apps.proposals.generator import build_section_prompt
        prompt = build_section_prompt(
            section_name="Technical Approach",
            requirements="Describe your methodology.",
            org_profile={"name": "Test Org"},
            reviewer_feedback="Add more detail on SDOH screening.",
        )
        self.assertIn("Add more detail on SDOH screening", prompt)

    @pytest.mark.asyncio
    async def test_clean_strips_preamble(self):
        from apps.proposals.generator import ProposalGenerator
        gen = ProposalGenerator.__new__(ProposalGenerator)
        gen.provider = "ollama"
        raw = "Here is the Technical Approach section:\n\n## Our Methodology\n\nContent here."
        cleaned = gen._clean(raw, "Technical Approach")
        self.assertFalse(cleaned.startswith("Here is"))
        self.assertIn("## Our Methodology", cleaned)

    @pytest.mark.asyncio
    async def test_clean_strips_trailing_note(self):
        from apps.proposals.generator import ProposalGenerator
        gen = ProposalGenerator.__new__(ProposalGenerator)
        gen.provider = "ollama"
        raw = "## Section Content\n\nGood content.\n\nNote: This is AI generated."
        cleaned = gen._clean(raw, "Section")
        self.assertNotIn("Note:", cleaned)


@override_settings(LLM_CONFIG=LLM_CONFIG_OLLAMA)
class TestComplianceChecker(TestCase):

    @pytest.mark.asyncio
    async def test_hipaa_check_flags_missing(self):
        from apps.compliance.checker import ComplianceChecker
        checker = ComplianceChecker()
        issues = checker._check_hipaa(
            "Technical Approach",
            "We store patient data and EHR records in our system."
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "hipaa")
        self.assertEqual(issues[0].severity, "error")

    @pytest.mark.asyncio
    async def test_hipaa_check_passes_when_addressed(self):
        from apps.compliance.checker import ComplianceChecker
        checker = ComplianceChecker()
        issues = checker._check_hipaa(
            "Technical Approach",
            "We store patient data and PHI following our full HIPAA compliance programme with BAA."
        )
        self.assertEqual(len(issues), 0)

    @pytest.mark.asyncio
    async def test_page_limit_flags_over_limit(self):
        from apps.compliance.checker import ComplianceChecker
        checker = ComplianceChecker()
        long_content = " ".join(["word"] * 1500)   # 1500 words > 5 pages (1375 words)
        issues = checker._check_page_limit("Technical Approach", long_content, 5, None)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "page_limit")

    @pytest.mark.asyncio
    async def test_page_limit_passes_within_limit(self):
        from apps.compliance.checker import ComplianceChecker
        checker = ComplianceChecker()
        short_content = " ".join(["word"] * 500)   # 500 words < 5 pages
        issues = checker._check_page_limit("Technical Approach", short_content, 5, None)
        self.assertEqual(len(issues), 0)

    @pytest.mark.asyncio
    async def test_cert_check_flags_missing_cert(self):
        from apps.compliance.checker import ComplianceChecker
        checker = ComplianceChecker()
        issues = checker._check_certifications(
            "Technical Approach",
            "We use secure systems for patient management.",
            ["HIPAA", "HITRUST"],
        )
        self.assertGreater(len(issues), 0)
        types = [i.issue_type for i in issues]
        self.assertIn("missing_cert", types)

    @pytest.mark.asyncio
    async def test_cert_check_passes_when_present(self):
        from apps.compliance.checker import ComplianceChecker
        checker = ComplianceChecker()
        issues = checker._check_certifications(
            "Technical Approach",
            "We are HIPAA compliant and HITRUST certified.",
            ["HIPAA", "HITRUST"],
        )
        self.assertEqual(len(issues), 0)

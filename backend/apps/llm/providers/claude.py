"""
apps/llm/providers/claude.py
Anthropic Claude provider — chat and streaming.
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from apps.llm.base import BaseLLMProvider


class ClaudeProvider(BaseLLMProvider):
    """
    Anthropic Claude provider.
    Requires ANTHROPIC_API_KEY in .env.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.model   = config.get("model", "claude-opus-4-5")

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file "
                "or switch to provider=ollama."
            )

        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    async def chat(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> str:
        kwargs = dict(
            model       = self.model,
            max_tokens  = max_tokens,
            messages    = messages,
            temperature = temperature,
        )
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)
        return response.content[0].text

    async def stream(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> AsyncIterator[str]:
        kwargs = dict(
            model       = self.model,
            max_tokens  = max_tokens,
            messages    = messages,
            temperature = temperature,
        )
        if system:
            kwargs["system"] = system

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def health_check(self) -> dict:
        try:
            # Simple test call
            await self._client.messages.create(
                model      = self.model,
                max_tokens = 10,
                messages   = [{"role": "user", "content": "Hi"}],
            )
            return {"provider": "claude", "status": "healthy", "model": self.model}
        except Exception as exc:
            return {"provider": "claude", "status": "unavailable", "error": str(exc)}

    async def list_models(self) -> list[str]:
        return [
            "claude-opus-4-5",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ]

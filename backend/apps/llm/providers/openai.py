"""
apps/llm/providers/openai.py
OpenAI GPT-4o provider — chat and streaming.
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from apps.llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI GPT-4o provider.
    Requires OPENAI_API_KEY in .env.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.model   = config.get("model", "gpt-4o")

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your .env file "
                "or switch to provider=ollama."
            )

        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=self.api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    async def chat(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> str:
        all_msgs = ([{"role": "system", "content": system}] if system else []) + messages
        response = await self._client.chat.completions.create(
            model       = self.model,
            messages    = all_msgs,
            temperature = temperature,
            max_tokens  = max_tokens,
        )
        return response.choices[0].message.content

    async def stream(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> AsyncIterator[str]:
        all_msgs = ([{"role": "system", "content": system}] if system else []) + messages
        async with self._client.chat.completions.stream(
            model       = self.model,
            messages    = all_msgs,
            temperature = temperature,
            max_tokens  = max_tokens,
        ) as stream:
            async for event in stream:
                token = event.choices[0].delta.content
                if token:
                    yield token

    async def health_check(self) -> dict:
        try:
            models = await self._client.models.list()
            return {
                "provider": "openai",
                "status":   "healthy",
                "model":    self.model,
            }
        except Exception as exc:
            return {"provider": "openai", "status": "unavailable", "error": str(exc)}

    async def list_models(self) -> list[str]:
        models = await self._client.models.list()
        return [m.id for m in models.data if "gpt" in m.id]

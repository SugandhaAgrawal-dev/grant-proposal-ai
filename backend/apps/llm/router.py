"""
apps/llm/router.py

Multi-LLM Router
================
Unified interface for Ollama, OpenAI, Claude, and Vertex AI (Gemini).
Switch provider via DEFAULT_LLM_PROVIDER in .env or pass provider= per call.

Usage:
    router = LLMRouter()                         # uses DEFAULT_LLM_PROVIDER
    router = LLMRouter(provider="vertex")        # force Vertex AI / Gemini
    router = LLMRouter(provider="ollama")        # force Ollama (local)
    router = LLMRouter(provider="openai")        # force OpenAI GPT-4o
    router = LLMRouter(provider="claude")        # force Claude

    # Non-streaming
    response = await router.chat(
        messages=[{"role": "user", "content": "Write a technical approach section."}],
        system="You are a healthcare grant writer.",
        temperature=0.35,
        max_tokens=3000,
    )

    # Streaming
    async for token in router.stream(messages, system):
        print(token, end="", flush=True)

    # Embeddings
    # vertex  → text-embedding-004 (768-dim, HIPAA-eligible)
    # ollama  → nomic-embed-text   (768-dim, local/free)
    vector = await router.embed("HIPAA compliance measures for Medi-Cal")

    # List available models for a provider
    models = await router.list_models()
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from django.conf import settings

from apps.llm.providers.ollama import OllamaProvider
from apps.llm.providers.openai import OpenAIProvider
from apps.llm.providers.claude import ClaudeProvider
from apps.llm.providers.vertex import VertexAIProvider
from apps.llm.base             import BaseLLMProvider


class LLMRouter:
    """
    Single entry point for all LLM operations.
    Automatically selects the configured provider and delegates all calls.
    """

    PROVIDERS = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "vertex": VertexAIProvider,
    }

    def __init__(self, provider: Optional[str] = None):
        config = settings.LLM_CONFIG
        self.provider_name = provider or config["default_provider"]

        if self.provider_name not in self.PROVIDERS:
            raise ValueError(
                f"Unknown provider: '{self.provider_name}'. "
                f"Choose from: {list(self.PROVIDERS.keys())}"
            )

        provider_config          = config.get(self.provider_name, {})
        self._provider: BaseLLMProvider = self.PROVIDERS[self.provider_name](provider_config)

    async def chat(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> str:
        """Generate a completion. Returns full response string."""
        return await self._provider.chat(
            messages    = messages,
            system      = system,
            temperature = temperature,
            max_tokens  = max_tokens,
        )

    async def stream(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> AsyncIterator[str]:
        """Stream tokens as they are generated."""
        async for token in self._provider.stream(
            messages    = messages,
            system      = system,
            temperature = temperature,
            max_tokens  = max_tokens,
        ):
            yield token

    async def embed(self, text: str) -> list[float]:
        """
        Generate a 768-dim embedding vector.

        Provider preference for embeddings:
          vertex → text-embedding-004 (HIPAA-eligible, best for production)
          ollama → nomic-embed-text   (free, local, same 768-dim)
          others → falls back to Ollama

        Both produce 768-dim vectors compatible with the pgvector column.
        """
        if self.provider_name == "vertex":
            return await self._provider.embed(text)

        # Default to Ollama for local/free embeddings
        ollama_config = settings.LLM_CONFIG.get("ollama", {})
        ollama = OllamaProvider(ollama_config)
        return await ollama.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple texts.
        Vertex AI supports native batching (up to 250 per call).
        Ollama uses concurrent individual calls.
        """
        if self.provider_name == "vertex":
            return await self._provider.embed_batch(texts)

        ollama_config = settings.LLM_CONFIG.get("ollama", {})
        ollama = OllamaProvider(ollama_config)
        return await ollama.embed_batch(texts)

    async def health_check(self) -> dict:
        """Check provider availability and return status dict."""
        return await self._provider.health_check()

    async def list_models(self) -> list[str]:
        """List available models for the active provider."""
        return await self._provider.list_models()

    @property
    def provider(self) -> str:
        return self.provider_name

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls.PROVIDERS.keys())

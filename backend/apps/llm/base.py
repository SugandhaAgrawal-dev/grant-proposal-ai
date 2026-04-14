"""apps/llm/base.py — Abstract base class for all LLM providers."""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class BaseLLMProvider(ABC):

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> str:
        """Return full completion string."""

    @abstractmethod
    async def stream(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> AsyncIterator[str]:
        """Yield tokens as they arrive."""

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(f"{self.__class__.__name__} does not support embeddings.")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        return await asyncio.gather(*[self.embed(t) for t in texts])

    async def health_check(self) -> dict:
        return {"provider": self.__class__.__name__, "status": "unknown"}

    async def list_models(self) -> list[str]:
        return []

"""
apps/llm/providers/ollama.py
Ollama local LLM provider — chat, stream, and embeddings.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from apps.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """
    Connects to a locally running Ollama instance.
    Supports: chat, streaming, embeddings.
    No API key required.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url   = config.get("base_url",    "http://localhost:11434")
        self.llm_model  = config.get("llm_model",   "llama3.1:8b")
        self.embed_model= config.get("embed_model",  "nomic-embed-text")
        self.timeout    = config.get("timeout",      120)
        self._client    = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=10),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    async def chat(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> str:
        all_msgs = ([{"role": "system", "content": system}] if system else []) + messages
        payload = {
            "model":   self.llm_model,
            "messages": all_msgs,
            "stream":   False,
            "options":  {"temperature": temperature, "num_predict": max_tokens},
        }
        r = await self._client.post("/api/chat", json=payload)
        r.raise_for_status()
        return r.json()["message"]["content"]

    async def stream(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> AsyncIterator[str]:
        all_msgs = ([{"role": "system", "content": system}] if system else []) + messages
        payload = {
            "model":   self.llm_model,
            "messages": all_msgs,
            "stream":   True,
            "options":  {"temperature": temperature, "num_predict": max_tokens},
        }
        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5), reraise=True)
    async def embed(self, text: str) -> list[float]:
        r = await self._client.post(
            "/api/embeddings",
            json={"model": self.embed_model, "prompt": text},
        )
        r.raise_for_status()
        return r.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        sem = asyncio.Semaphore(6)
        async def _one(t):
            async with sem:
                return await self.embed(t)
        return await asyncio.gather(*[_one(t) for t in texts])

    async def health_check(self) -> dict:
        try:
            r = await self._client.get("/api/tags")
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            return {
                "provider": "ollama",
                "status":   "healthy",
                "llm_model": self.llm_model,
                "embed_model": self.embed_model,
                "llm_available":   any(self.llm_model   in m for m in models),
                "embed_available": any(self.embed_model in m for m in models),
                "all_models": models,
            }
        except Exception as exc:
            return {"provider": "ollama", "status": "unavailable", "error": str(exc)}

    async def list_models(self) -> list[str]:
        r = await self._client.get("/api/tags")
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

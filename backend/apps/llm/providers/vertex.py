"""
apps/llm/providers/vertex.py

Google Vertex AI Provider
==========================
Supports:
  - Chat completion  : Gemini 1.5 Pro / Gemini 2.0 Flash
  - Streaming        : token-by-token via Vertex AI streaming API
  - Embeddings       : text-embedding-004 (768-dim, same as nomic-embed-text)

Requirements:
  pip install google-cloud-aiplatform

Authentication (one of):
  1. Service account JSON key  → set GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
  2. Application Default Credentials (ADC) → run: gcloud auth application-default login
  3. Workload Identity (GKE / Cloud Run)  → automatic

.env variables needed:
  GOOGLE_CLOUD_PROJECT=your-gcp-project-id
  GOOGLE_CLOUD_LOCATION=us-central1
  VERTEX_LLM_MODEL=gemini-1.5-pro-002           (or gemini-2.0-flash-001)
  VERTEX_EMBED_MODEL=text-embedding-004
  GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json   (if using service account)

Supported Gemini models:
  gemini-1.5-pro-002       — best quality, 1M token context
  gemini-1.5-flash-002     — faster, cheaper, 1M token context
  gemini-2.0-flash-001     — latest flash, strong coding + reasoning
  gemini-1.0-pro-002       — stable, lower cost
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from apps.llm.base import BaseLLMProvider


class VertexAIProvider(BaseLLMProvider):
    """
    Google Vertex AI provider using the google-cloud-aiplatform SDK.

    Gemini models on Vertex AI differ from the Google AI Studio (Gemini API):
    - Vertex AI is enterprise-grade, HIPAA-eligible, VPC-SC compatible
    - Vertex AI supports grounding, system instructions, and tuned models
    - Pricing is per 1K characters, not per token
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.project   = config.get("project",     "")
        self.location  = config.get("location",    "us-central1")
        self.llm_model = config.get("llm_model",   "gemini-1.5-pro-002")
        self.embed_model = config.get("embed_model","text-embedding-004")

        if not self.project:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT is not set. "
                "Add it to your .env file: GOOGLE_CLOUD_PROJECT=your-gcp-project-id"
            )

        self._init_clients()

    def _init_clients(self):
        """Initialise Vertex AI SDK clients."""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            from vertexai.language_models import TextEmbeddingModel

            vertexai.init(project=self.project, location=self.location)
            self._generative_model_cls = GenerativeModel
            self._embed_model_cls      = TextEmbeddingModel
            self._llm_client = GenerativeModel(
                model_name=self.llm_model,
            )
        except ImportError:
            raise ImportError(
                "google-cloud-aiplatform is not installed. "
                "Run: pip install google-cloud-aiplatform"
            )

    # ── Chat completion ───────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15), reraise=True)
    async def chat(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> str:
        """
        Non-streaming Gemini completion via Vertex AI.

        Converts OpenAI-style messages to Gemini's Content format.
        System prompt is passed via system_instruction parameter.
        """
        from vertexai.generative_models import (
            GenerativeModel,
            GenerationConfig,
            Content,
            Part,
        )

        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        # Rebuild client with system instruction if provided
        if system:
            client = GenerativeModel(
                model_name=self.llm_model,
                system_instruction=system,
            )
        else:
            client = self._llm_client

        # Convert messages to Gemini Content format
        gemini_contents = self._convert_messages(messages)

        # Run sync SDK in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.generate_content(
                gemini_contents,
                generation_config=generation_config,
            ),
        )

        return response.text

    async def stream(
        self,
        messages:    list[dict],
        system:      Optional[str] = None,
        temperature: float         = 0.35,
        max_tokens:  int           = 3000,
    ) -> AsyncIterator[str]:
        """
        Streaming Gemini completion — yields text chunks as they arrive.
        """
        from vertexai.generative_models import (
            GenerativeModel,
            GenerationConfig,
        )

        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        if system:
            client = GenerativeModel(
                model_name=self.llm_model,
                system_instruction=system,
            )
        else:
            client = self._llm_client

        gemini_contents = self._convert_messages(messages)

        # Run streaming in thread pool, yield chunks
        loop   = asyncio.get_event_loop()
        queue  = asyncio.Queue()

        def _stream_worker():
            try:
                for chunk in client.generate_content(
                    gemini_contents,
                    generation_config=generation_config,
                    stream=True,
                ):
                    if chunk.text:
                        asyncio.run_coroutine_threadsafe(
                            queue.put(chunk.text), loop
                        )
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(queue.put(exc), loop)

        loop.run_in_executor(None, _stream_worker)

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item

    # ── Embeddings ────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    async def embed(self, text: str) -> list[float]:
        """
        Generate a 768-dim embedding using Vertex AI text-embedding-004.

        Same dimensionality as nomic-embed-text, compatible with existing
        pgvector columns.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embed_sync, text)

    def _embed_sync(self, text: str) -> list[float]:
        model      = self._embed_model_cls.from_pretrained(self.embed_model)
        embeddings = model.get_embeddings([text])
        return embeddings[0].values

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts — Vertex AI supports batching natively."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embed_batch_sync, texts)

    def _embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        model      = self._embed_model_cls.from_pretrained(self.embed_model)
        # Vertex AI supports up to 250 texts per batch call
        results    = []
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch      = texts[i : i + batch_size]
            embeddings = model.get_embeddings(batch)
            results.extend([e.values for e in embeddings])
        return results

    # ── Health check ──────────────────────────────────────────────────────────

    async def health_check(self) -> dict:
        """Verify Vertex AI credentials and project access."""
        try:
            # Quick test generation
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._llm_client.generate_content(
                    "Say OK in one word."
                ),
            )
            return {
                "provider":    "vertex",
                "status":      "healthy",
                "project":     self.project,
                "location":    self.location,
                "llm_model":   self.llm_model,
                "embed_model": self.embed_model,
                "response":    response.text.strip(),
            }
        except Exception as exc:
            return {
                "provider": "vertex",
                "status":   "unavailable",
                "project":  self.project,
                "error":    str(exc),
                "hint": (
                    "Check: 1) GOOGLE_CLOUD_PROJECT is set, "
                    "2) Credentials are configured "
                    "(GOOGLE_APPLICATION_CREDENTIALS or gcloud auth application-default login), "
                    "3) Vertex AI API is enabled in your GCP project."
                ),
            }

    async def list_models(self) -> list[str]:
        return [
            "gemini-1.5-pro-002",
            "gemini-1.5-flash-002",
            "gemini-2.0-flash-001",
            "gemini-1.0-pro-002",
        ]

    # ── Message conversion ────────────────────────────────────────────────────

    def _convert_messages(self, messages: list[dict]):
        """
        Convert OpenAI-style messages to Gemini Content objects.

        OpenAI:  [{"role": "user", "content": "Hello"}]
        Gemini:  [Content(role="user", parts=[Part.from_text("Hello")])]

        Note: Gemini uses "model" instead of "assistant" for role names.
        """
        from vertexai.generative_models import Content, Part

        gemini_messages = []
        for msg in messages:
            role    = msg["role"]
            content = msg["content"]

            # Gemini uses "model" not "assistant"
            if role == "assistant":
                role = "model"

            # Skip system messages — handled via system_instruction
            if role == "system":
                continue

            gemini_messages.append(
                Content(role=role, parts=[Part.from_text(content)])
            )

        return gemini_messages

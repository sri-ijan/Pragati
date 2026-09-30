"""
SetuAI — Embeddings Provider Boundary (Slice 4)

Separate from services/llm_provider.py's LLMProvider (chat/structured-output)
abstraction: embeddings are a genuinely different capability, and Groq does
not offer an embeddings API at all, so there is no "primary/fallback" pair
here — only Gemini. This means semantic retrieval specifically requires
GEMINI_API_KEY even if extraction/reranking are running on Groq alone; that's
a real constraint, not a bug, and is documented in docs/DECISIONS.md.

get_embeddings_provider() raises EmbeddingsProviderNotConfigured when
GEMINI_API_KEY is unset — callers must fail clearly, never fall back to a
fake/zero embedding.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from config.settings import settings

# 768 dimensions: a well-established, moderate size for gemini-embedding-001
# (which supports up to 3072) — enough quality for semantic retrieval over a
# few hundred schedule activities without an oversized pgvector index.
EMBEDDING_DIMENSIONS = 768


class EmbeddingsProviderNotConfigured(RuntimeError):
    """Raised when no embeddings provider is usable — callers must fail clearly."""


class EmbeddingsError(RuntimeError):
    """Raised when an embeddings call fails for any reason."""


class EmbeddingsProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        """Returns one embedding vector per input text, same order. `is_query`
        selects Gemini's asymmetric task type (RETRIEVAL_QUERY vs
        RETRIEVAL_DOCUMENT) for better retrieval quality."""
        raise NotImplementedError


class GeminiEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, api_key: str, model: str):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        from google.genai import errors, types

        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
        try:
            response = self._client.models.embed_content(
                model=self._model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBEDDING_DIMENSIONS,
                ),
            )
        except (errors.ClientError, errors.ServerError) as exc:
            raise EmbeddingsError(f"Gemini embeddings call failed: {exc}") from exc

        if not response.embeddings or len(response.embeddings) != len(texts):
            raise EmbeddingsError(
                f"Gemini returned {len(response.embeddings or [])} embeddings for "
                f"{len(texts)} inputs — expected one each."
            )
        return [list(e.values) for e in response.embeddings]


def get_embeddings_provider() -> EmbeddingsProvider:
    if not settings.gemini_api_key:
        raise EmbeddingsProviderNotConfigured(
            "No embeddings provider is configured. Semantic matching requires "
            "GEMINI_API_KEY (Groq does not offer an embeddings API)."
        )
    return GeminiEmbeddingsProvider(api_key=settings.gemini_api_key, model=settings.gemini_embedding_model)
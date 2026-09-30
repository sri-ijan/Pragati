"""
SetuAI — LLM Provider Boundary (Slice 3, revised; extended in Slice 4)

Abstracts two LLM capabilities behind one small interface so concrete
providers can be swapped/added without touching extraction_service.py,
matching_service.py, or any API route:
  - extract_fields: schema-constrained field-report extraction (Slice 3)
  - rerank_candidates: scoring a short list of schedule-activity candidates
    against a described field event (Slice 4)

Provider policy (per explicit instruction — do not change without a new
instruction): Groq is the PRIMARY provider for BOTH capabilities. Gemini is
the AUTOMATIC FALLBACK, used only when Groq fails for an availability-class
reason (rate limit, quota exhaustion, connection failure, 5xx/temporary
provider error) — never merely because the returned data looks wrong; that's
a separate concern handled by the calling service's own validation, which
runs after a provider already returned something. Anthropic was removed
entirely per instruction: no Anthropic dependency, config, or code path
remains. (Embeddings for semantic retrieval are a separate concern — see
services/embeddings_provider.py — since Groq has no embeddings API at all.)

get_llm_provider() raises LLMProviderNotConfigured only when NEITHER
GROQ_API_KEY nor GEMINI_API_KEY is set. Callers must surface configuration
and extraction/reranking failures as clear errors — never fall back to
guessing or a fake response.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

from config.settings import settings

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Single source of truth for what the LLM may extract. event_id, source_id
# and raw_text are always set by our own code (services/extraction_service.py)
# — never by the model, and the model is never asked for them.
# ---------------------------------------------------------------------------

_EXTRACTION_FIELDS: list[tuple[str, str, str]] = [
    ("activity_description", "string", "Short description of the work described in the text."),
    (
        "discipline",
        "string",
        "One of Civil, Piping, Electrical, Instrumentation — only if explicitly stated OR "
        "unambiguous from standard terminology (cable tray/conduit/panel/breaker -> Electrical; "
        "pipeline/spool/weld/hydrotest/valve -> Piping; foundation/concrete/rebar/earthwork -> "
        "Civil; transmitter/gauge/instrument loop/calibration -> Instrumentation). Otherwise "
        "null — do not guess.",
    ),
    (
        "action",
        "string",
        "Short verb/phrase for the work being done, e.g. 'installation', 'erection', 'testing', "
        "'progress update'.",
    ),
    (
        "status",
        "string",
        "One of started, in_progress, completed, hold, cancelled — only if the text supports it. "
        "A stated partial/percentage completion means in_progress, not completed.",
    ),
    ("location", "string", "Physical location/area mentioned in the text, if any."),
    ("equipment_tag", "string", "Equipment tag if explicitly named in the text, else null."),
    ("line_number", "string", "Line number if explicitly named in the text, else null."),
    (
        "event_date",
        "string",
        "ISO date (YYYY-MM-DD) ONLY if an explicit calendar date is stated in the text. Never "
        "infer 'today'. Never convert relative terms like 'tomorrow'/'kal'/'yesterday' into a "
        "date — leave null in that case.",
    ),
    (
        "quantity",
        "number",
        "A stated numeric quantity or percentage, if any (e.g. 60 for '60% done').",
    ),
    ("unit", "string", "Unit for quantity if stated (e.g. '%', 'm', 'inch')."),
]

SYSTEM_PROMPT = (
    "You extract structured facts from construction-site field reports for a "
    "schedule-reconciliation system. Respond only with the requested structured "
    "fields. Rules, no exceptions: "
    "1) Never invent an activity/schedule ID — none is ever requested here. "
    "2) Never invent or infer a date; only use an explicit calendar date "
    "found in the text, otherwise leave event_date null — 'tomorrow', 'kal', "
    "'today' are NOT dates. "
    "3) Never invent a completion percentage or quantity; only report one if "
    "the text states it. "
    "4) Do not silently convert uncertain or ambiguous information into a "
    "firm fact — use null instead. "
    "5) discipline may be set from unambiguous standard terminology even if "
    "the word itself isn't in the text (e.g. 'cable tray' clearly implies "
    "Electrical) — but if there is no such signal, leave it null. "
    "Text may be in English, Hindi, or a mix (Hinglish)."
)


def _groq_json_schema() -> dict[str, Any]:
    """OpenAI-style JSON Schema for Groq's response_format={'type': 'json_schema', strict: true}.
    Strict mode requires every property listed in 'required' and additionalProperties: false —
    nullability is expressed via a ["type", "null"] union per property instead."""
    return {
        "type": "object",
        "properties": {
            name: {"type": [jtype, "null"], "description": desc}
            for name, jtype, desc in _EXTRACTION_FIELDS
        },
        "required": [name for name, _, _ in _EXTRACTION_FIELDS],
        "additionalProperties": False,
    }


def _gemini_response_schema() -> dict[str, Any]:
    """Gemini's schema format is an OpenAPI 3.0 subset: uppercase type names, and
    nullability via 'nullable': true rather than a type union. 'required' is left
    empty deliberately — we want the model free to omit/null fields it can't
    support, not forced to invent a non-null value to satisfy a required key."""
    return {
        "type": "OBJECT",
        "properties": {
            name: {"type": jtype.upper(), "nullable": True, "description": desc}
            for name, jtype, desc in _EXTRACTION_FIELDS
        },
    }


RERANK_SYSTEM_PROMPT = (
    "You score how well a short list of candidate schedule activities matches "
    "a described field event, for a construction schedule-reconciliation "
    "system. Score each candidate from 0.0 (no plausible match) to 1.0 "
    "(clearly the same activity). Base scores only on the action, object, "
    "location, and discipline compatibility between the event and each "
    "candidate's own description/discipline/area — never invent information "
    "about a candidate that isn't in the list you were given, and never "
    "introduce a candidate that wasn't given to you. Give 2-4 short reasons "
    "per candidate (e.g. 'same location', 'matching action', 'discipline "
    "mismatch') explaining the score."
)


def _rerank_input_schema(candidate_count: int) -> dict[str, Any]:
    """Groq strict-mode schema for the reranking response — an array with
    exactly one scored entry per candidate given."""
    return {
        "type": "object",
        "properties": {
            "rankings": {
                "type": "array",
                "minItems": candidate_count,
                "maxItems": candidate_count,
                "items": {
                    "type": "object",
                    "properties": {
                        "candidate_activity_id": {"type": "string"},
                        "score": {"type": "number", "description": "0.0 to 1.0"},
                        "reasons": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["candidate_activity_id", "score", "reasons"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["rankings"],
        "additionalProperties": False,
    }


def _rerank_gemini_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "rankings": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "candidate_activity_id": {"type": "STRING"},
                        "score": {"type": "NUMBER", "description": "0.0 to 1.0"},
                        "reasons": {"type": "ARRAY", "items": {"type": "STRING"}},
                    },
                },
            }
        },
    }


def _format_candidates_for_prompt(candidates: list[dict[str, Any]]) -> str:
    lines = [
        f"- id={c['candidate_activity_id']} | discipline={c['discipline']} | "
        f"area={c['area']} | description={c['description']}"
        for c in candidates
    ]
    return "\n".join(lines)



class LLMProviderNotConfigured(RuntimeError):
    """Raised when NEITHER provider is usable — callers must fail clearly, not fake output."""


class LLMExtractionError(RuntimeError):
    """Raised when a provider call fails for a non-availability reason, or when both
    the primary and fallback provider have been exhausted."""


class LLMProviderUnavailable(LLMExtractionError):
    """Raised internally by a concrete provider for availability-class failures only:
    rate limiting, quota exhaustion, connection failure, or a temporary (5xx-style)
    provider error. This is the ONLY exception type that triggers automatic fallback
    from Groq to Gemini — never raised merely because the returned data looks wrong."""


class LLMProvider(ABC):
    @abstractmethod
    def extract_fields(self, raw_text: str) -> dict[str, Any]:
        """Returns a dict matching _EXTRACTION_FIELDS' names (values may be None)."""
        raise NotImplementedError

    @abstractmethod
    def rerank_candidates(
        self, event_summary: str, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Scores each candidate against the event. `candidates` is a list of dicts
        with candidate_activity_id/discipline/area/description. Returns a list of
        dicts with candidate_activity_id/score(0-1)/reasons(list[str]), one per
        input candidate (order not guaranteed to match input order)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Groq — PRIMARY provider
# ---------------------------------------------------------------------------


class GroqLLMProvider(LLMProvider):
    """Concrete provider — Groq's OpenAI-compatible Chat Completions API, with
    strict JSON-schema structured output (constrained decoding, never invalid JSON).
    Strict mode is currently only supported on openai/gpt-oss-20b and
    openai/gpt-oss-120b per Groq's docs — that's why it's the default GROQ_MODEL."""

    def __init__(self, api_key: str, model: str):
        # Imported lazily so the rest of services/ stays importable (e.g. for
        # tests using a fake provider) without requiring every SDK installed.
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._model = model

    def extract_fields(self, raw_text: str) -> dict[str, Any]:
        import groq

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": raw_text},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "record_execution_event",
                        "strict": True,
                        "schema": _groq_json_schema(),
                    },
                },
            )
        except groq.RateLimitError as exc:
            # Covers both per-minute rate limiting and quota exhaustion — Groq
            # (like most OpenAI-compatible APIs) uses 429 for both.
            raise LLMProviderUnavailable(f"Groq rate limit/quota exceeded: {exc}") from exc
        except groq.APIConnectionError as exc:
            raise LLMProviderUnavailable(f"Groq connection failure: {exc}") from exc
        except groq.InternalServerError as exc:
            raise LLMProviderUnavailable(f"Groq temporary server error: {exc}") from exc
        except groq.APIStatusError as exc:
            # Anything else 4xx (bad request, auth, permission, not found,
            # unprocessable) is a config/client-side problem, not a transient
            # availability issue — do not trigger fallback for these.
            raise LLMExtractionError(f"Groq API error ({exc.status_code}): {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMExtractionError("Groq response had no content.")

        import json

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMExtractionError(f"Groq response was not valid JSON: {exc}") from exc

    def rerank_candidates(
        self, event_summary: str, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        import groq

        user_message = (
            f"Field event: {event_summary}\n\nCandidate schedule activities:\n"
            f"{_format_candidates_for_prompt(candidates)}"
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": RERANK_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "rank_candidates",
                        "strict": True,
                        "schema": _rerank_input_schema(len(candidates)),
                    },
                },
            )
        except groq.RateLimitError as exc:
            raise LLMProviderUnavailable(f"Groq rate limit/quota exceeded: {exc}") from exc
        except groq.APIConnectionError as exc:
            raise LLMProviderUnavailable(f"Groq connection failure: {exc}") from exc
        except groq.InternalServerError as exc:
            raise LLMProviderUnavailable(f"Groq temporary server error: {exc}") from exc
        except groq.APIStatusError as exc:
            raise LLMExtractionError(f"Groq API error ({exc.status_code}): {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMExtractionError("Groq rerank response had no content.")

        import json

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMExtractionError(f"Groq rerank response was not valid JSON: {exc}") from exc

        return parsed.get("rankings", [])


# ---------------------------------------------------------------------------
# Gemini — AUTOMATIC FALLBACK provider
# ---------------------------------------------------------------------------


class GeminiLLMProvider(LLMProvider):
    """Concrete provider — Google's Gemini API (google-genai SDK), JSON mode
    with a response_schema for structured output."""

    def __init__(self, api_key: str, model: str):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def extract_fields(self, raw_text: str) -> dict[str, Any]:
        from google.genai import errors, types

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=raw_text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=_gemini_response_schema(),
                ),
            )
        except errors.ServerError as exc:
            raise LLMProviderUnavailable(f"Gemini temporary server error: {exc}") from exc
        except errors.ClientError as exc:
            if exc.code == 429:
                raise LLMProviderUnavailable(f"Gemini rate limit/quota exceeded: {exc}") from exc
            # Other 4xx (bad request, auth, permission, not found) is a
            # config/client-side problem, not a transient availability issue.
            raise LLMExtractionError(f"Gemini API error ({exc.code}): {exc}") from exc

        text = response.text
        if not text:
            raise LLMExtractionError("Gemini response had no content.")

        import json

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMExtractionError(f"Gemini response was not valid JSON: {exc}") from exc

    def rerank_candidates(
        self, event_summary: str, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        from google.genai import errors, types

        user_message = (
            f"Field event: {event_summary}\n\nCandidate schedule activities:\n"
            f"{_format_candidates_for_prompt(candidates)}"
        )
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=RERANK_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=_rerank_gemini_schema(),
                ),
            )
        except errors.ServerError as exc:
            raise LLMProviderUnavailable(f"Gemini temporary server error: {exc}") from exc
        except errors.ClientError as exc:
            if exc.code == 429:
                raise LLMProviderUnavailable(f"Gemini rate limit/quota exceeded: {exc}") from exc
            raise LLMExtractionError(f"Gemini API error ({exc.code}): {exc}") from exc

        text = response.text
        if not text:
            raise LLMExtractionError("Gemini rerank response had no content.")

        import json

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMExtractionError(f"Gemini rerank response was not valid JSON: {exc}") from exc

        return parsed.get("rankings", [])


# ---------------------------------------------------------------------------
# Fallback orchestration — Groq first, Gemini only on LLMProviderUnavailable
# ---------------------------------------------------------------------------


class _FallbackLLMProvider(LLMProvider):
    """Tries the primary provider; falls back to the secondary ONLY when the
    primary raises LLMProviderUnavailable. Any other exception from the
    primary (a non-availability failure, e.g. a malformed response) propagates
    immediately without attempting the fallback — per instruction, fallback is
    for provider availability problems only, not for "the data looked wrong."
    Applies identically to both extract_fields and rerank_candidates via the
    shared _call_with_fallback helper, so the policy can't drift between them."""

    def __init__(
        self,
        primary: LLMProvider | None,
        primary_name: str,
        fallback: LLMProvider | None,
        fallback_name: str,
    ):
        self._primary = primary
        self._primary_name = primary_name
        self._fallback = fallback
        self._fallback_name = fallback_name

    def _call_with_fallback(self, call: Callable[[LLMProvider], T]) -> T:
        primary_unavailable_reason: str | None = None

        if self._primary is not None:
            try:
                return call(self._primary)
            except LLMProviderUnavailable as exc:
                primary_unavailable_reason = str(exc)
                # falls through to fallback below
        else:
            primary_unavailable_reason = f"{self._primary_name} is not configured."

        if self._fallback is None:
            raise LLMExtractionError(
                f"{self._primary_name} was unavailable ({primary_unavailable_reason}) and no "
                f"fallback provider is configured."
            )

        try:
            return call(self._fallback)
        except LLMProviderUnavailable as exc:
            raise LLMExtractionError(
                f"{self._primary_name} was unavailable ({primary_unavailable_reason}) and "
                f"{self._fallback_name} was also unavailable ({exc})."
            ) from exc
        # Any other exception from the fallback (e.g. malformed response)
        # propagates as-is — it's already the last provider in the chain.

    def extract_fields(self, raw_text: str) -> dict[str, Any]:
        return self._call_with_fallback(lambda provider: provider.extract_fields(raw_text))

    def rerank_candidates(
        self, event_summary: str, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return self._call_with_fallback(
            lambda provider: provider.rerank_candidates(event_summary, candidates)
        )


def get_llm_provider() -> LLMProvider:
    groq_provider = (
        GroqLLMProvider(api_key=settings.groq_api_key, model=settings.groq_model)
        if settings.groq_api_key
        else None
    )
    gemini_provider = (
        GeminiLLMProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
        if settings.gemini_api_key
        else None
    )

    if groq_provider is None and gemini_provider is None:
        raise LLMProviderNotConfigured(
            "No LLM provider is configured. Set GROQ_API_KEY (primary) and/or "
            "GEMINI_API_KEY (automatic fallback) in your .env to enable extraction."
        )

    return _FallbackLLMProvider(
        primary=groq_provider,
        primary_name="Groq",
        fallback=gemini_provider,
        fallback_name="Gemini",
    )
    
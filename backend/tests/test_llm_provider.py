"""
Tests for services/llm_provider.py — provider configuration/selection and the
Groq-primary/Gemini-fallback orchestration logic.

Requirement 6 (missing provider config fails clearly): get_llm_provider()
itself is never mocked — only settings/API keys are patched away, so this
exercises the real selection logic.

Requirements for the Groq/Gemini fallback behavior use plain test doubles
implementing the LLMProvider interface (not the real SDKs) against the
internal _FallbackLLMProvider orchestrator directly — this is standard
"mock provider calls in unit tests" per instruction; the real GroqLLMProvider/
GeminiLLMProvider classes (which do call the real SDKs) are never used as a
fake/simulated success path anywhere here.
"""

from typing import Any

import pytest

from config.settings import settings
from services.llm_provider import (
    GeminiLLMProvider,
    GroqLLMProvider,
    LLMExtractionError,
    LLMProvider,
    LLMProviderNotConfigured,
    LLMProviderUnavailable,
    _FallbackLLMProvider,  # testing the orchestrator directly, same package
    get_llm_provider,
)

FAKE_GROQ_KEY = "gsk_fake_secret_should_never_leak_into_any_error_message"
FAKE_GEMINI_KEY = "AIzaFakeSecretShouldNeverLeakIntoAnyErrorMessage"


class _SpyProvider(LLMProvider):
    """A test double that records whether it was called, and either returns a
    canned result or raises a canned exception — used to prove call/no-call
    behavior without touching a real LLM API. Both interface methods share
    the same call-recording/raise logic since the fallback tests only care
    about call/no-call and success/failure, not which method was invoked."""

    def __init__(self, *, result: dict[str, Any] | None = None, raises: Exception | None = None):
        self.called = False
        self._result = result
        self._raises = raises

    def _call(self) -> dict[str, Any]:
        self.called = True
        if self._raises is not None:
            raise self._raises
        return self._result or {}

    def extract_fields(self, raw_text: str) -> dict[str, Any]:
        return self._call()

    def rerank_candidates(self, event_summary: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self._call()


# ---------------------------------------------------------------------------
# get_llm_provider() — configuration / selection (real logic, keys patched)
# ---------------------------------------------------------------------------


def test_raises_clearly_when_neither_provider_configured(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "gemini_api_key", None)

    with pytest.raises(LLMProviderNotConfigured, match="GROQ_API_KEY"):
        get_llm_provider()


def test_succeeds_when_only_groq_configured(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", FAKE_GROQ_KEY)
    monkeypatch.setattr(settings, "gemini_api_key", None)

    assert get_llm_provider() is not None


def test_succeeds_when_only_gemini_configured(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_GEMINI_KEY)

    assert get_llm_provider() is not None


def test_succeeds_when_both_configured(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", FAKE_GROQ_KEY)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_GEMINI_KEY)

    assert get_llm_provider() is not None


# ---------------------------------------------------------------------------
# Fallback orchestration (_FallbackLLMProvider) — the four required proofs
# ---------------------------------------------------------------------------


def test_groq_success_gemini_not_called():
    """Requirement: Groq success -> Gemini is NOT called."""
    groq = _SpyProvider(result={"activity_description": "ok"})
    gemini = _SpyProvider(result={"activity_description": "should never be used"})
    provider = _FallbackLLMProvider(primary=groq, primary_name="Groq", fallback=gemini, fallback_name="Gemini")

    result = provider.extract_fields("some field report text")

    assert result == {"activity_description": "ok"}
    assert groq.called is True
    assert gemini.called is False


def test_groq_availability_failure_falls_back_to_gemini():
    """Requirement: Groq quota/rate-limit/provider failure -> Gemini is called."""
    groq = _SpyProvider(raises=LLMProviderUnavailable("Groq rate limit/quota exceeded: 429"))
    gemini = _SpyProvider(result={"activity_description": "from gemini"})
    provider = _FallbackLLMProvider(primary=groq, primary_name="Groq", fallback=gemini, fallback_name="Gemini")

    result = provider.extract_fields("some field report text")

    assert result == {"activity_description": "from gemini"}
    assert groq.called is True
    assert gemini.called is True


def test_groq_and_gemini_both_fail_raises_standard_error():
    """Requirement: Groq failure + Gemini failure -> standard error behavior
    (LLMExtractionError — the same type api/extraction.py already catches and
    maps to 502 LLM_EXTRACTION_FAILED; no new error handling path needed)."""
    groq = _SpyProvider(raises=LLMProviderUnavailable("Groq rate limit/quota exceeded: 429"))
    gemini = _SpyProvider(raises=LLMProviderUnavailable("Gemini rate limit/quota exceeded: 429"))
    provider = _FallbackLLMProvider(primary=groq, primary_name="Groq", fallback=gemini, fallback_name="Gemini")

    with pytest.raises(LLMExtractionError) as exc_info:
        provider.extract_fields("some field report text")

    assert groq.called is True
    assert gemini.called is True
    assert "Groq" in str(exc_info.value)
    assert "Gemini" in str(exc_info.value)


def test_non_availability_failure_does_not_trigger_fallback():
    """Fallback is for provider AVAILABILITY problems only — a non-availability
    failure (e.g. malformed response) from Groq must propagate immediately,
    never triggering a Gemini call, per 'do not fallback merely because the
    extracted data is invalid.'"""
    groq = _SpyProvider(raises=LLMExtractionError("Groq response was not valid JSON"))
    gemini = _SpyProvider(result={"activity_description": "should never be reached"})
    provider = _FallbackLLMProvider(primary=groq, primary_name="Groq", fallback=gemini, fallback_name="Gemini")

    with pytest.raises(LLMExtractionError, match="not valid JSON"):
        provider.extract_fields("some field report text")

    assert groq.called is True
    assert gemini.called is False


def test_groq_not_configured_falls_back_to_gemini_immediately():
    """Missing Groq configuration is itself treated as an availability
    problem — Gemini should still be tried without erroring first."""
    gemini = _SpyProvider(result={"activity_description": "from gemini only"})
    provider = _FallbackLLMProvider(primary=None, primary_name="Groq", fallback=gemini, fallback_name="Gemini")

    result = provider.extract_fields("some field report text")

    assert result == {"activity_description": "from gemini only"}
    assert gemini.called is True


# ---------------------------------------------------------------------------
# API keys must never be exposed
# ---------------------------------------------------------------------------


def test_api_keys_never_appear_in_configuration_error_message(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "gemini_api_key", None)

    with pytest.raises(LLMProviderNotConfigured) as exc_info:
        get_llm_provider()

    assert FAKE_GROQ_KEY not in str(exc_info.value)
    assert FAKE_GEMINI_KEY not in str(exc_info.value)


def test_api_keys_never_appear_in_fallback_error_message():
    groq = _SpyProvider(raises=LLMProviderUnavailable(f"Groq call failed (key ending ...{FAKE_GROQ_KEY[-4:]} not used here)"))
    gemini = _SpyProvider(raises=LLMProviderUnavailable("Gemini also failed"))
    provider = _FallbackLLMProvider(primary=groq, primary_name="Groq", fallback=gemini, fallback_name="Gemini")

    with pytest.raises(LLMExtractionError) as exc_info:
        provider.extract_fields("text")

    assert FAKE_GROQ_KEY not in str(exc_info.value)
    assert FAKE_GEMINI_KEY not in str(exc_info.value)


def test_provider_instances_do_not_retain_raw_api_key_as_an_attribute(monkeypatch):
    """GroqLLMProvider/GeminiLLMProvider pass the key straight into the SDK
    client constructor and never store it themselves — confirms there's no
    `self._api_key`/`self.api_key` a log/debugger dump could leak."""
    groq_provider = GroqLLMProvider(api_key=FAKE_GROQ_KEY, model="openai/gpt-oss-20b")
    gemini_provider = GeminiLLMProvider(api_key=FAKE_GEMINI_KEY, model="gemini-2.5-flash")

    for provider in (groq_provider, gemini_provider):
        for value in vars(provider).values():
            assert FAKE_GROQ_KEY != value
            assert FAKE_GEMINI_KEY != value
        assert FAKE_GROQ_KEY not in repr(provider)
        assert FAKE_GEMINI_KEY not in repr(provider)
"""Tests for services/embeddings_provider.py's configuration/selection logic."""

import pytest

from config.settings import settings
from services.embeddings_provider import EmbeddingsProviderNotConfigured, get_embeddings_provider

FAKE_GEMINI_KEY = "AIzaFakeSecretShouldNeverLeakIntoAnyErrorMessage"


def test_raises_clearly_when_gemini_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)

    with pytest.raises(EmbeddingsProviderNotConfigured, match="GEMINI_API_KEY"):
        get_embeddings_provider()


def test_succeeds_when_gemini_configured(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_GEMINI_KEY)

    assert get_embeddings_provider() is not None


def test_error_message_never_contains_the_actual_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)

    with pytest.raises(EmbeddingsProviderNotConfigured) as exc_info:
        get_embeddings_provider()

    assert FAKE_GEMINI_KEY not in str(exc_info.value)
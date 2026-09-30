"""
Tests for services/extraction_service.py — the orchestration/validation logic.

Uses a deterministic FakeLLMProvider instead of a real provider (Groq/Gemini),
per the Slice 3 instructions: mock providers are for tests only, never for the
application's real runtime path (see services/llm_provider.get_llm_provider,
tested separately in test_llm_provider.py, which is never mocked).
"""

from datetime import date
from typing import Any

import pytest

from models.schemas import Discipline, EventStatus
from services.extraction_service import (
    ExtractionIncomplete,
    ExtractionInput,
    extract_execution_event,
)
from services.llm_provider import LLMProvider


class FakeLLMProvider(LLMProvider):
    """Returns a canned dict instead of calling a real LLM — test-only."""

    def __init__(self, fields: dict[str, Any]):
        self._fields = fields

    def extract_fields(self, raw_text: str) -> dict[str, Any]:
        return self._fields

    def rerank_candidates(self, event_summary: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError("not used by extraction tests")


UPLOADED_AT = date(2026, 9, 20)


def _make_input(text: str, filename: str = "field-update.txt") -> ExtractionInput:
    return ExtractionInput(
        source_document_id="doc-123",
        project_id="proj-123",
        filename=filename,
        file_bytes=text.encode("utf-8"),
        uploaded_at=UPLOADED_AT,
    )


def test_valid_field_evidence_produces_a_full_execution_event():
    """Requirement 1: valid field evidence goes through the extraction path end to end."""
    raw_text = "Cable tray installation at Rack B is mostly complete, around 60% done."
    provider = FakeLLMProvider(
        {
            "activity_description": "Cable tray installation",
            "discipline": "Electrical",
            "action": "installation",
            "status": "in_progress",
            "location": "Rack B",
            "equipment_tag": None,
            "line_number": None,
            "event_date": None,  # no explicit date stated
            "quantity": 60,
            "unit": "%",
        }
    )

    event = extract_execution_event(provider, _make_input(raw_text))

    assert event.discipline == Discipline.ELECTRICAL
    assert event.status == EventStatus.IN_PROGRESS
    assert event.location == "Rack B"
    assert event.quantity == 60
    assert event.unit == "%"
    assert event.event_id.startswith("EVT-")
    assert event.source_id == "doc-123"


def test_output_is_validated_against_canonical_schema_stray_enum_value_rejected():
    """Requirement 2: LLM output is validated against the canonical schema — a
    discipline value outside the closed vocabulary must not be silently accepted."""
    provider = FakeLLMProvider(
        {
            "activity_description": "Some work",
            "discipline": "NotARealDiscipline",  # hallucinated / invalid enum value
            "action": "installation",
            "status": "in_progress",
            "location": "Rack B",
            "equipment_tag": None,
            "line_number": None,
            "event_date": None,
            "quantity": None,
            "unit": None,
        }
    )

    with pytest.raises(ExtractionIncomplete) as exc_info:
        extract_execution_event(provider, _make_input("some text"))

    assert "discipline" in exc_info.value.missing_fields


def test_unsupported_fields_are_not_invented_missing_required_field_fails_cleanly():
    """Requirement 3: fields the LLM can't determine must not be guessed —
    extraction must fail with a clear, listed reason instead."""
    provider = FakeLLMProvider(
        {
            "activity_description": None,  # LLM genuinely couldn't determine this
            "discipline": "Piping",
            "action": "installation",
            "status": "in_progress",
            "location": "Rack B",
            "equipment_tag": None,
            "line_number": None,
            "event_date": None,
            "quantity": None,
            "unit": None,
        }
    )

    with pytest.raises(ExtractionIncomplete) as exc_info:
        extract_execution_event(provider, _make_input("ambiguous text"))

    assert exc_info.value.missing_fields == ["activity_description"]


def test_no_explicit_date_falls_back_to_upload_date_not_invented_by_llm():
    """Requirement 3 (dates specifically): the LLM returning event_date=None
    (because the text only says 'kal'/tomorrow, not an actual date) must not
    be converted into a guessed date by the LLM — the fallback used is the
    source document's real upload date, applied deterministically in code."""
    provider = FakeLLMProvider(
        {
            "activity_description": "Cable tray installation",
            "discipline": "Electrical",
            "action": "installation",
            "status": "in_progress",
            "location": "Rack B",
            "equipment_tag": None,
            "line_number": None,
            "event_date": None,  # LLM correctly did not invent a date for "kal"
            "quantity": 60,
            "unit": "%",
        }
    )

    event = extract_execution_event(provider, _make_input("... kal remaining section pe kaam karegi."))

    assert event.event_date == UPLOADED_AT


def test_explicit_date_in_text_is_used_over_the_fallback():
    provider = FakeLLMProvider(
        {
            "activity_description": "Cable tray installation",
            "discipline": "Electrical",
            "action": "installation",
            "status": "completed",
            "location": "Rack B",
            "equipment_tag": None,
            "line_number": None,
            "event_date": "2026-09-15",  # explicitly stated in the source text
            "quantity": None,
            "unit": None,
        }
    )

    event = extract_execution_event(provider, _make_input("Completed on 15 Sept 2026."))

    assert event.event_date == date(2026, 9, 15)


def test_raw_evidence_is_preserved_exactly():
    """Requirement 4: raw evidence must be preserved, unmodified, on the event."""
    raw_text = "Rack B mein cable tray ka kaam mostly complete ho gaya hai, around 60% done."
    provider = FakeLLMProvider(
        {
            "activity_description": "Cable tray installation",
            "discipline": "Electrical",
            "action": "installation",
            "status": "in_progress",
            "location": "Rack B",
            "equipment_tag": None,
            "line_number": None,
            "event_date": None,
            "quantity": 60,
            "unit": "%",
        }
    )

    event = extract_execution_event(provider, _make_input(raw_text))

    assert event.raw_text == raw_text
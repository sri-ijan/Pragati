"""
SetuAI — Extraction Service (Slice 3)

Field evidence -> text extraction -> schema-constrained LLM call -> validated
ExecutionEvent. The LLM only ever fills in the fields defined by
services/llm_provider.py's tool schema; event_id, source_id and raw_text are
always set here, never by the model.

Two design decisions worth flagging explicitly (also in the Slice 3 report
and docs/DECISIONS.md — NOT a change to the locked ExecutionEvent contract,
but a real judgment call about how to satisfy it):

1. event_date is a REQUIRED field on the locked ExecutionEvent schema, but
   the extraction rules correctly forbid ever inventing a date. When the LLM
   finds no explicit date in the text (as in the Hindi/English example with
   only "kal"/tomorrow — a reference to future work, not this event's own
   date), this module falls back to the source document's upload date. That
   is real metadata (the actual time the report was filed), not a guess, and
   the LLM itself never sees or produces this value — the fallback is applied
   here, deterministically, after the LLM call returns. This is a standard
   "daily progress report" convention (the report's date, absent contrary
   evidence, is presumed to be the day it was filed) — but it IS a policy
   choice, not something the locked schema or the extraction rules dictate
   outright, so it's called out rather than buried.

2. For every OTHER required field (activity_description, discipline, action,
   status, location), if the LLM legitimately can't determine it, it stays
   null and extraction fails cleanly (ExtractionIncomplete) rather than
   guessing. No fallback is applied to these — only event_date has one,
   because only event_date has no other honest way to be satisfied at all
   without either failing (undesirable per the given example) or a schema
   change (avoided per instructions).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from models.schemas import Discipline, EventStatus, ExecutionEvent
from services.document_text_extractor import extract_text
from services.llm_provider import LLMProvider


class ExtractionIncomplete(RuntimeError):
    """Raised when a required ExecutionEvent field can't be determined from the
    source without guessing. Carries which fields were missing for the API to report."""

    def __init__(self, missing_fields: list[str]):
        self.missing_fields = missing_fields
        super().__init__(f"Could not determine required field(s): {', '.join(missing_fields)}")


@dataclass
class ExtractionInput:
    source_document_id: str
    project_id: str
    filename: str
    file_bytes: bytes
    uploaded_at: date  # used only as the event_date fallback — see module docstring


def _coerce_discipline(value: object) -> Discipline | None:
    if value is None:
        return None
    try:
        return Discipline(value)
    except ValueError:
        return None  # outside the closed vocabulary — treat as unknown, never guess


def _coerce_status(value: object) -> EventStatus | None:
    if value is None:
        return None
    try:
        return EventStatus(value)
    except ValueError:
        return None


def _coerce_date(value: object) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None  # malformed — treat as not-stated rather than crash


def _clean_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_execution_event(provider: LLMProvider, doc: ExtractionInput) -> ExecutionEvent:
    raw_text = extract_text(doc.filename, doc.file_bytes)  # raises UnsupportedForExtraction

    fields = provider.extract_fields(raw_text)

    discipline = _coerce_discipline(fields.get("discipline"))
    status = _coerce_status(fields.get("status"))
    activity_description = _clean_str(fields.get("activity_description"))
    action = _clean_str(fields.get("action"))
    location = _clean_str(fields.get("location"))
    event_date = _coerce_date(fields.get("event_date")) or doc.uploaded_at

    missing = [
        name
        for name, value in [
            ("activity_description", activity_description),
            ("discipline", discipline),
            ("action", action),
            ("status", status),
            ("location", location),
        ]
        if value is None
    ]
    if missing:
        raise ExtractionIncomplete(missing)

    return ExecutionEvent(
        event_id=f"EVT-{uuid4()}",
        source_id=doc.source_document_id,
        discipline=discipline,
        activity_description=activity_description,
        action=action,
        status=status,
        location=location,
        equipment_tag=_clean_str(fields.get("equipment_tag")),
        line_number=_clean_str(fields.get("line_number")),
        event_date=event_date,
        quantity=fields.get("quantity"),
        unit=_clean_str(fields.get("unit")),
        raw_text=raw_text,
        confidence=None,  # not applicable until Slice 4 matching
    )
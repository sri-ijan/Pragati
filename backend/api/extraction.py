"""
SetuAI — Extraction Router (Slice 3)

POST /projects/{id}/extract — contracted in docs/API.md.
GET  /projects/{id}/events  — contracted in docs/API.md.

Orchestrates: load source_document -> extract text -> schema-constrained LLM
call -> validated ExecutionEvent -> persist -> return. Never fakes a result —
a missing LLM provider, an unreadable document, or an extraction that can't
determine a required field all fail with a clear error in the standard
envelope, not a guessed ExecutionEvent.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config.database import get_db
from models.schemas import ExecutionEvent, ExtractResponse
from repositories import execution_event_repository, project_repository
from repositories.document_repository import get_documents_for_project
from services.document_text_extractor import UnsupportedForExtraction
from services.extraction_service import (
    ExtractionIncomplete,
    ExtractionInput,
    extract_execution_event,
)
from services.llm_provider import (
    LLMExtractionError,
    LLMProviderNotConfigured,
    get_llm_provider,
)

router = APIRouter(prefix="/projects", tags=["extraction"])


def _get_project_or_404(db: Session, project_id: str):
    project = project_repository.get_project(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Project '{project_id}' does not exist.",
                }
            },
        )
    return project


class ExtractRequest(BaseModel):
    source_document_id: str


@router.post("/{project_id}/extract", response_model=ExtractResponse)
def extract(project_id: str, body: ExtractRequest, db: Session = Depends(get_db)) -> ExtractResponse:
    _get_project_or_404(db, project_id)

    # Reuses the existing document listing rather than adding a new
    # single-document repository method — document volume per project is
    # small enough that this isn't a real cost.
    doc = next(
        (
            d
            for d in get_documents_for_project(db, project_id)
            if d.source_document_id == body.source_document_id
        ),
        None,
    )
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Document '{body.source_document_id}' does not exist for this project.",
                }
            },
        )

    try:
        provider = get_llm_provider()
    except LLMProviderNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "LLM_PROVIDER_NOT_CONFIGURED", "message": str(exc)}},
        ) from exc

    file_bytes = Path(doc.storage_path).read_bytes()
    extraction_input = ExtractionInput(
        source_document_id=doc.source_document_id,
        project_id=project_id,
        filename=doc.filename,
        file_bytes=file_bytes,
        uploaded_at=doc.uploaded_at.date(),
    )

    try:
        event = extract_execution_event(provider, extraction_input)
    except UnsupportedForExtraction as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "UNSUPPORTED_FOR_EXTRACTION", "message": str(exc)}},
        ) from exc
    except ExtractionIncomplete as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "EXTRACTION_INCOMPLETE",
                    "message": str(exc),
                    "details": {"missing_fields": exc.missing_fields},
                }
            },
        ) from exc
    except LLMExtractionError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "LLM_EXTRACTION_FAILED", "message": str(exc)}},
        ) from exc

    execution_event_repository.save_execution_event(db, project_id, event)
    return ExtractResponse(events=[event])


@router.get("/{project_id}/events", response_model=list[ExecutionEvent])
def list_events(
    project_id: str, status: str | None = None, db: Session = Depends(get_db)
) -> list[ExecutionEvent]:
    _get_project_or_404(db, project_id)
    rows = execution_event_repository.get_events_for_project(db, project_id, status)
    return [
        ExecutionEvent(
            event_id=r.event_id,
            source_id=r.source_id,
            discipline=r.discipline,
            activity_description=r.activity_description,
            action=r.action,
            status=r.status,
            location=r.location,
            equipment_tag=r.equipment_tag,
            line_number=r.line_number,
            event_date=r.event_date,
            quantity=r.quantity,
            unit=r.unit,
            raw_text=r.raw_text,
            confidence=r.confidence,
        )
        for r in rows
    ]
"""
SetuAI — Matching Router (Slice 4)

POST /events/{id}/match — contracted in docs/API.md (no project_id in the
URL — the event already knows its own project).
GET  /events/{id}/candidates — contracted in docs/API.md; re-reads the last
computed batch without recomputing.

Never fakes a result: a missing embeddings/LLM provider, an unknown event, or
zero candidates surviving the hard filter all produce a clear, honest
response — not a guessed match.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from models.schemas import MatchDecision, MatchRecord, MatchResponse
from repositories import execution_event_repository, match_repository, schedule_repository
from services.embeddings_provider import EmbeddingsError, EmbeddingsProviderNotConfigured, get_embeddings_provider
from services.llm_provider import LLMProviderNotConfigured, get_llm_provider
from services.matching_service import MatchInput, ScheduleActivityCandidate, find_matches

router = APIRouter(prefix="/events", tags=["matching"])


def _get_event_or_404(db: Session, event_id: str):
    event = execution_event_repository.get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": f"Event '{event_id}' does not exist."}},
        )
    return event


@router.post("/{event_id}/match", response_model=MatchResponse)
def match(event_id: str, db: Session = Depends(get_db)) -> MatchResponse:
    event_row = _get_event_or_404(db, event_id)

    activities = schedule_repository.get_activities_for_project(db, event_row.project_id)
    candidates = [
        ScheduleActivityCandidate(
            activity_id=a.activity_id,
            discipline=a.discipline,
            description=a.description,
            area=a.area,
            planned_start=a.planned_start,
            planned_finish=a.planned_finish,
        )
        for a in activities
    ]

    try:
        embeddings_provider = get_embeddings_provider()
    except EmbeddingsProviderNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "EMBEDDINGS_PROVIDER_NOT_CONFIGURED", "message": str(exc)}},
        ) from exc

    try:
        llm_provider = get_llm_provider()
    except LLMProviderNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "LLM_PROVIDER_NOT_CONFIGURED", "message": str(exc)}},
        ) from exc

    match_input = MatchInput(
        event_id=event_row.event_id,
        discipline=event_row.discipline,
        activity_description=event_row.activity_description,
        action=event_row.action,
        location=event_row.location,
        event_date=event_row.event_date,
    )

    try:
        matches = find_matches(
            db,
            event_row.project_id,
            match_input,
            candidates,
            embeddings_provider,
            llm_provider,
        )
    except EmbeddingsError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "EMBEDDINGS_FAILED", "message": str(exc)}},
        ) from exc

    match_repository.replace_matches(db, event_id, matches)
    return MatchResponse(event_id=event_id, candidates=matches)


@router.get("/{event_id}/candidates", response_model=MatchResponse)
def candidates(event_id: str, db: Session = Depends(get_db)) -> MatchResponse:
    _get_event_or_404(db, event_id)

    rows = match_repository.get_matches_for_event(db, event_id)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"No match has been computed yet for event '{event_id}'. "
                    f"Call POST /events/{event_id}/match first.",
                }
            },
        )

    return MatchResponse(
        event_id=event_id,
        candidates=[
            MatchRecord(
                event_id=r.event_id,
                candidate_activity_id=r.candidate_activity_id,
                semantic_score=r.semantic_score,
                metadata_score=r.metadata_score,
                temporal_score=r.temporal_score,
                llm_score=r.llm_score,
                terminology_score=r.terminology_score,
                final_confidence=r.final_confidence,
                decision=MatchDecision(r.decision),
                reviewer=r.reviewer,
                reason=r.reason,
            )
            for r in rows
        ],
    )
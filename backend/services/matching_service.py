"""
SetuAI — Matching Service (Slice 4)

Field event -> hard filter -> semantic retrieval (embeddings + pgvector) ->
LLM reranking -> deterministic validation -> weighted confidence ->
MatchRecord candidates.

Reuses the Slice 3 LLMProvider boundary (rerank_candidates) and a separate
EmbeddingsProvider (Gemini-only — see services/embeddings_provider.py) for
semantic retrieval. This module never decides which concrete provider to
use — that's entirely get_llm_provider()/get_embeddings_provider()'s job,
same "don't hardcode provider selection in business logic" principle as
Slice 3's extraction_service.py.

terminology_score is now a first-class field on the locked MatchRecord
contract (previously a flagged gap — CONFIDENCE_WEIGHTS included a
"terminology" component with nowhere to store it; resolved by adding the
field to models/schemas.py and shared/types.ts — see docs/DECISIONS.md for
the full history of that decision).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from models.schemas import CONFIDENCE_WEIGHTS, MatchRecord, decision_for_confidence
from repositories import embedding_repository
from services.embeddings_provider import EmbeddingsProvider
from services.llm_provider import LLMExtractionError, LLMProvider

# How far outside an activity's planned window an event date can fall before
# temporal_score hits zero. A generous buffer — field reports are often a few
# days off from the plan; that alone shouldn't disqualify a match.
TEMPORAL_BUFFER_DAYS = 14

# Candidates kept after semantic retrieval, before LLM reranking — keeps the
# reranking prompt small and cheap regardless of schedule size.
DEFAULT_TOP_K = 8


@dataclass
class ScheduleActivityCandidate:
    activity_id: str
    discipline: str
    description: str
    area: str
    planned_start: date
    planned_finish: date


@dataclass
class MatchInput:
    event_id: str
    discipline: str
    activity_description: str
    action: str
    location: str
    event_date: date


# ---------------------------------------------------------------------------
# Stage 1 — hard filter
# ---------------------------------------------------------------------------


def hard_filter(
    event: MatchInput, activities: list[ScheduleActivityCandidate]
) -> list[ScheduleActivityCandidate]:
    """The only HARD exclusion is discipline mismatch — a clean, exact
    comparison over the same 4-value canonical enum on both sides. Location/
    area naming varies too much in practice to hard-exclude on; that's scored
    instead (metadata_score), not filtered away here."""
    return [a for a in activities if a.discipline == event.discipline]


# ---------------------------------------------------------------------------
# Stage 4 components — deterministic scoring (run per surviving candidate)
# ---------------------------------------------------------------------------


def _metadata_score(
    event: MatchInput, candidate: ScheduleActivityCandidate
) -> tuple[float, list[str]]:
    """Discipline is already guaranteed equal by hard_filter — this scores the
    softer structural signal: location/area token overlap."""
    reasons = [f"Same discipline ({event.discipline})"]

    event_tokens = set(event.location.lower().split())
    area_tokens = set(candidate.area.lower().split())
    if event_tokens and area_tokens:
        if event_tokens & area_tokens:
            location_score = 1.0
            reasons.append(f"Location overlap: {candidate.area}")
        else:
            location_score = 0.3  # some credit — naming conventions vary
    else:
        location_score = 0.5  # nothing to compare either way

    return (0.5 * 1.0 + 0.5 * location_score), reasons


def _temporal_score(
    event: MatchInput, candidate: ScheduleActivityCandidate
) -> tuple[float, list[str]]:
    if candidate.planned_start <= event.event_date <= candidate.planned_finish:
        return 1.0, ["Event date falls within the planned schedule window"]

    gap = (
        (candidate.planned_start - event.event_date).days
        if event.event_date < candidate.planned_start
        else (event.event_date - candidate.planned_finish).days
    )

    if gap >= TEMPORAL_BUFFER_DAYS:
        return 0.0, [f"Event date is {gap} days outside the planned schedule window"]

    return 1.0 - (gap / TEMPORAL_BUFFER_DAYS), [
        f"Event date is {gap} day(s) outside the planned schedule window"
    ]


def _terminology_score(
    event: MatchInput, candidate: ScheduleActivityCandidate
) -> tuple[float, list[str]]:
    """Lightweight token overlap between the event's own description/action
    text and the candidate's description. Folds into final_confidence per
    CONFIDENCE_WEIGHTS['terminology'], and is exposed directly as
    MatchRecord.terminology_score."""
    event_tokens = set(f"{event.activity_description} {event.action}".lower().split())
    candidate_tokens = set(candidate.description.lower().split())
    if not event_tokens or not candidate_tokens:
        return 0.5, []

    overlap = event_tokens & candidate_tokens
    score = min(1.0, len(overlap) / max(1, len(event_tokens)))
    reasons = [f"Shared terminology: {', '.join(sorted(overlap))}"] if overlap else []
    return score, reasons


def score_candidate(
    event: MatchInput,
    candidate: ScheduleActivityCandidate,
    semantic_score: float,
    llm_score: float,
    llm_reasons: list[str],
) -> MatchRecord:
    metadata_score, metadata_reasons = _metadata_score(event, candidate)
    temporal_score, temporal_reasons = _temporal_score(event, candidate)
    terminology_score, terminology_reasons = _terminology_score(event, candidate)

    final_confidence = (
        CONFIDENCE_WEIGHTS["semantic"] * semantic_score
        + CONFIDENCE_WEIGHTS["metadata"] * metadata_score
        + CONFIDENCE_WEIGHTS["llm_rerank"] * llm_score
        + CONFIDENCE_WEIGHTS["temporal"] * temporal_score
        + CONFIDENCE_WEIGHTS["terminology"] * terminology_score
    )
    final_confidence = max(0.0, min(1.0, final_confidence))

    reasons = (
        metadata_reasons
        + [f"Semantic similarity: {semantic_score:.2f}"]
        + llm_reasons
        + temporal_reasons
        + terminology_reasons
    )

    return MatchRecord(
        event_id=event.event_id,
        candidate_activity_id=candidate.activity_id,
        semantic_score=round(semantic_score, 4),
        metadata_score=round(metadata_score, 4),
        temporal_score=round(temporal_score, 4),
        llm_score=round(llm_score, 4),
        terminology_score=round(terminology_score, 4),
        final_confidence=round(final_confidence, 4),
        decision=decision_for_confidence(final_confidence),
        reviewer=None,
        reason=reasons,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def find_matches(
    db: Session,
    project_id: str,
    event: MatchInput,
    activities: list[ScheduleActivityCandidate],
    embeddings_provider: EmbeddingsProvider,
    llm_provider: LLMProvider,
    top_k: int = DEFAULT_TOP_K,
) -> list[MatchRecord]:
    """Runs the full pipeline and returns scored MatchRecords, sorted by
    final_confidence descending. Returns an empty list if hard filtering
    leaves no candidates (e.g. no schedule activities of that discipline)."""
    filtered = hard_filter(event, activities)
    if not filtered:
        return []

    by_id = {a.activity_id: a for a in filtered}

    # Stage 2 — semantic retrieval (embeddings + pgvector).
    cached_ids = embedding_repository.get_cached_activity_ids(db, project_id)
    missing = [a for a in filtered if a.activity_id not in cached_ids]
    if missing:
        texts = [f"{a.description}. {a.area}." for a in missing]
        vectors = embeddings_provider.embed(texts, is_query=False)
        embedding_repository.save_embeddings(
            db, project_id, {a.activity_id: v for a, v in zip(missing, vectors)}
        )

    query_text = f"{event.activity_description}. {event.action}. {event.location}."
    query_embedding = embeddings_provider.embed([query_text], is_query=True)[0]

    top_similar = embedding_repository.top_k_similar(
        db, project_id, query_embedding, [a.activity_id for a in filtered], k=top_k
    )
    if not top_similar:
        return []

    # Stage 3 — LLM reranking, only on the semantically-retrieved shortlist.
    event_summary = (
        f"{event.activity_description} — {event.action} at {event.location} "
        f"(discipline: {event.discipline})"
    )
    candidate_dicts = [
        {
            "candidate_activity_id": activity_id,
            "discipline": by_id[activity_id].discipline,
            "area": by_id[activity_id].area,
            "description": by_id[activity_id].description,
        }
        for activity_id, _ in top_similar
    ]

    try:
        rankings = llm_provider.rerank_candidates(event_summary, candidate_dicts)
    except LLMExtractionError:
        # Reranking failed entirely (both providers, or the only configured
        # one) — proceed with llm_score=0 for every candidate rather than
        # fabricating a rank, so confidence correctly reflects "no LLM signal
        # was available" instead of a fake one.
        rankings = []

    llm_by_id: dict[str, tuple[float, list[str]]] = {}
    for entry in rankings:
        candidate_id = entry.get("candidate_activity_id")
        if not candidate_id:
            continue
        score = entry.get("score")
        llm_by_id[candidate_id] = (
            max(0.0, min(1.0, float(score))) if isinstance(score, (int, float)) else 0.0,
            [str(r) for r in entry.get("reasons", [])],
        )

    # Stage 4 — deterministic validation + confidence, per candidate.
    matches = [
        score_candidate(
            event,
            by_id[activity_id],
            semantic_score=similarity,
            llm_score=llm_by_id.get(activity_id, (0.0, []))[0],
            llm_reasons=llm_by_id.get(activity_id, (0.0, []))[1],
        )
        for activity_id, similarity in top_similar
    ]

    matches.sort(key=lambda m: m.final_confidence, reverse=True)
    return matches
"""Tests for repositories/match_repository.py — save/replace + retrieval."""

from models.schemas import MatchDecision, MatchRecord
from repositories.match_repository import get_matches_for_event, replace_matches


def _match(event_id: str, candidate_id: str, confidence: float, decision: MatchDecision) -> MatchRecord:
    return MatchRecord(
        event_id=event_id,
        candidate_activity_id=candidate_id,
        semantic_score=0.8,
        metadata_score=0.7,
        temporal_score=1.0,
        llm_score=0.9,
        terminology_score=0.6,
        final_confidence=confidence,
        decision=decision,
        reviewer=None,
        reason=["Same discipline", "Semantic similarity: 0.80"],
    )


def test_matches_persist_and_are_retrievable_sorted_by_confidence(db_session):
    matches = [
        _match("EVT-1", "ELE-101", 0.95, MatchDecision.AUTO_MATCH),
        _match("EVT-1", "ELE-102", 0.75, MatchDecision.REVIEW_REQUIRED),
    ]

    replace_matches(db_session, event_id="EVT-1", matches=matches)
    rows = get_matches_for_event(db_session, event_id="EVT-1")

    assert [r.candidate_activity_id for r in rows] == ["ELE-101", "ELE-102"]
    assert rows[0].decision == "auto_match"
    assert rows[0].reason == ["Same discipline", "Semantic similarity: 0.80"]


def test_terminology_score_propagates_through_persistence(db_session):
    """Proves terminology_score survives MatchRecord -> ORM -> DB -> ORM ->
    round trip, not just that the field exists."""
    replace_matches(
        db_session, event_id="EVT-1", matches=[_match("EVT-1", "ELE-101", 0.9, MatchDecision.AUTO_MATCH)]
    )

    rows = get_matches_for_event(db_session, event_id="EVT-1")

    assert rows[0].terminology_score == 0.6


def test_a_fresh_match_run_replaces_not_accumulates(db_session):
    replace_matches(db_session, event_id="EVT-1", matches=[_match("EVT-1", "ELE-101", 0.9, MatchDecision.AUTO_MATCH)])
    replace_matches(db_session, event_id="EVT-1", matches=[_match("EVT-1", "ELE-999", 0.5, MatchDecision.UNMATCHED)])

    rows = get_matches_for_event(db_session, event_id="EVT-1")

    assert len(rows) == 1
    assert rows[0].candidate_activity_id == "ELE-999"


def test_matches_scoped_to_their_own_event(db_session):
    replace_matches(db_session, event_id="EVT-A", matches=[_match("EVT-A", "ELE-1", 0.9, MatchDecision.AUTO_MATCH)])
    replace_matches(db_session, event_id="EVT-B", matches=[_match("EVT-B", "ELE-2", 0.5, MatchDecision.UNMATCHED)])

    assert len(get_matches_for_event(db_session, "EVT-A")) == 1
    assert len(get_matches_for_event(db_session, "EVT-B")) == 1
    assert get_matches_for_event(db_session, "EVT-A")[0].candidate_activity_id == "ELE-1"
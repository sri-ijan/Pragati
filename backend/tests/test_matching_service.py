"""
Tests for services/matching_service.py's pure scoring logic (hard filter,
per-component scores, confidence composition) — no DB, no providers. The
orchestration function find_matches() (which touches the DB and both
providers) is tested separately in test_matching_orchestration.py with
everything mocked/faked.
"""

from datetime import date

import pytest

from models.schemas import CONFIDENCE_WEIGHTS, MatchDecision
from services.matching_service import (
    MatchInput,
    ScheduleActivityCandidate,
    TEMPORAL_BUFFER_DAYS,
    _metadata_score,
    _temporal_score,
    _terminology_score,
    hard_filter,
    score_candidate,
)


def _event(**overrides) -> MatchInput:
    defaults = dict(
        event_id="EVT-1",
        discipline="Electrical",
        activity_description="Cable tray installation",
        action="installation",
        location="Rack B",
        event_date=date(2026, 9, 10),
    )
    defaults.update(overrides)
    return MatchInput(**defaults)


def _activity(**overrides) -> ScheduleActivityCandidate:
    defaults = dict(
        activity_id="ELE-101",
        discipline="Electrical",
        description="Install cable tray at Rack B",
        area="Rack B",
        planned_start=date(2026, 9, 8),
        planned_finish=date(2026, 9, 12),
    )
    defaults.update(overrides)
    return ScheduleActivityCandidate(**defaults)


# ---------------------------------------------------------------------------
# Stage 1 — hard filter
# ---------------------------------------------------------------------------


def test_hard_filter_excludes_different_discipline():
    event = _event(discipline="Electrical")
    activities = [
        _activity(activity_id="ELE-101", discipline="Electrical"),
        _activity(activity_id="PIP-101", discipline="Piping"),
        _activity(activity_id="CIV-101", discipline="Civil"),
    ]

    result = hard_filter(event, activities)

    assert [a.activity_id for a in result] == ["ELE-101"]


def test_hard_filter_keeps_all_same_discipline_candidates():
    event = _event(discipline="Piping")
    activities = [_activity(activity_id="PIP-1", discipline="Piping"), _activity(activity_id="PIP-2", discipline="Piping")]

    assert len(hard_filter(event, activities)) == 2


# ---------------------------------------------------------------------------
# Stage 4 components
# ---------------------------------------------------------------------------


def test_metadata_score_full_credit_for_location_overlap():
    event = _event(location="Rack B")
    activity = _activity(area="Rack B")

    score, reasons = _metadata_score(event, activity)

    assert score == 1.0
    assert any("Rack B" in r for r in reasons)


def test_metadata_score_partial_credit_when_location_does_not_overlap():
    event = _event(location="Rack B")
    activity = _activity(area="Unit 3")

    score, _ = _metadata_score(event, activity)

    # 0.5 * discipline(1.0) + 0.5 * location(0.3) = 0.65
    assert 0.6 < score < 0.7


def test_temporal_score_full_credit_within_window():
    event = _event(event_date=date(2026, 9, 10))
    activity = _activity(planned_start=date(2026, 9, 8), planned_finish=date(2026, 9, 12))

    score, reasons = _temporal_score(event, activity)

    assert score == 1.0
    assert "within" in reasons[0]


def test_temporal_score_decays_linearly_outside_window():
    activity = _activity(planned_start=date(2026, 9, 8), planned_finish=date(2026, 9, 12))
    # 7 days after planned_finish, buffer is TEMPORAL_BUFFER_DAYS=14
    event = _event(event_date=date(2026, 9, 19))

    score, _ = _temporal_score(event, activity)

    assert score == pytest.approx(1.0 - 7 / TEMPORAL_BUFFER_DAYS)


def test_temporal_score_zero_beyond_buffer():
    activity = _activity(planned_start=date(2026, 9, 8), planned_finish=date(2026, 9, 12))
    event = _event(event_date=date(2026, 11, 1))  # far outside any reasonable buffer

    score, _ = _temporal_score(event, activity)

    assert score == 0.0


def test_terminology_score_rewards_shared_words():
    event = _event(activity_description="cable tray installation", action="installation")
    activity = _activity(description="install cable tray at rack b")

    score, reasons = _terminology_score(event, activity)

    assert score > 0
    assert reasons  # some shared-terminology reason was produced


# ---------------------------------------------------------------------------
# Confidence composition (score_candidate)
# ---------------------------------------------------------------------------


def test_score_candidate_uses_the_exact_locked_confidence_formula():
    event = _event()
    activity = _activity()

    match = score_candidate(
        event, activity, semantic_score=0.8, llm_score=0.9, llm_reasons=["Matching action and location"]
    )

    metadata_score, _ = _metadata_score(event, activity)
    temporal_score, _ = _temporal_score(event, activity)
    terminology_score, _ = _terminology_score(event, activity)

    expected = (
        CONFIDENCE_WEIGHTS["semantic"] * 0.8
        + CONFIDENCE_WEIGHTS["metadata"] * metadata_score
        + CONFIDENCE_WEIGHTS["llm_rerank"] * 0.9
        + CONFIDENCE_WEIGHTS["temporal"] * temporal_score
        + CONFIDENCE_WEIGHTS["terminology"] * terminology_score
    )

    assert abs(match.final_confidence - round(expected, 4)) < 1e-6
    assert abs(match.terminology_score - round(terminology_score, 4)) < 1e-6


def test_score_candidate_exposes_terminology_score_as_its_own_field():
    """Proves the previously-flagged contract gap is resolved: terminology_score
    is a real, retrievable field on MatchRecord — not just folded silently
    into final_confidence."""
    event = _event(activity_description="cable tray installation", action="installation")
    activity = _activity(description="install cable tray at rack b")

    match = score_candidate(event, activity, semantic_score=0.5, llm_score=0.5, llm_reasons=[])

    expected_terminology_score, _ = _terminology_score(event, activity)
    assert match.terminology_score == round(expected_terminology_score, 4)
    assert 0.0 <= match.terminology_score <= 1.0


def test_score_candidate_high_scores_produce_auto_match_decision():
    event = _event()
    activity = _activity()

    match = score_candidate(event, activity, semantic_score=1.0, llm_score=1.0, llm_reasons=[])

    assert match.decision == MatchDecision.AUTO_MATCH
    assert match.final_confidence >= 0.90


def test_score_candidate_low_scores_produce_unmatched_decision():
    event = _event()
    activity = _activity(area="Somewhere Else Entirely", description="Unrelated work")

    match = score_candidate(event, activity, semantic_score=0.0, llm_score=0.0, llm_reasons=[])

    assert match.decision == MatchDecision.UNMATCHED


def test_score_candidate_includes_event_and_candidate_ids():
    event = _event(event_id="EVT-42")
    activity = _activity(activity_id="ELE-999")

    match = score_candidate(event, activity, semantic_score=0.5, llm_score=0.5, llm_reasons=[])

    assert match.event_id == "EVT-42"
    assert match.candidate_activity_id == "ELE-999"


def test_score_candidate_reason_list_is_never_empty_for_a_filtered_candidate():
    # Every surviving candidate passed the discipline hard filter, so
    # _metadata_score always contributes at least the "same discipline" reason.
    event = _event()
    activity = _activity()

    match = score_candidate(event, activity, semantic_score=0.5, llm_score=0.0, llm_reasons=[])

    assert len(match.reason) > 0
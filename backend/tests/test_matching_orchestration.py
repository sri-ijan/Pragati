"""
Tests for services/matching_service.find_matches — the full pipeline
orchestration. Uses fake EmbeddingsProvider/LLMProvider (deterministic,
test-only, never the runtime path) and monkeypatches repositories.embedding_repository
directly rather than hitting real Postgres/pgvector, since pgvector's SQL
operators aren't available on SQLite and a real Postgres instance isn't
assumed to be present wherever this test suite runs. The pgvector-backed SQL
query itself (embedding_repository.top_k_similar) is covered separately in
test_embedding_repository_pgvector.py, which skips itself if Postgres with
the vector extension isn't reachable.
"""

from datetime import date
from typing import Any

from models.schemas import MatchDecision
from services.embeddings_provider import EmbeddingsProvider
from services.llm_provider import LLMExtractionError, LLMProvider
from services.matching_service import MatchInput, ScheduleActivityCandidate, find_matches

import repositories.embedding_repository as embedding_repository


class FakeEmbeddingsProvider(EmbeddingsProvider):
    """Returns a fixed-size deterministic vector per text (hash-based, not
    semantically meaningful) — good enough to prove the orchestration wiring
    without a real embeddings call."""

    def embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        return [[float((hash(t) % 100) + i) for i in range(4)] for t in texts]


class FakeLLMProvider(LLMProvider):
    def __init__(self, rankings: list[dict[str, Any]] | None = None, raises: Exception | None = None):
        self._rankings = rankings or []
        self._raises = raises

    def extract_fields(self, raw_text: str) -> dict[str, Any]:
        raise NotImplementedError("not used by matching tests")

    def rerank_candidates(self, event_summary: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self._raises:
            raise self._raises
        return self._rankings


def _event() -> MatchInput:
    return MatchInput(
        event_id="EVT-1",
        discipline="Electrical",
        activity_description="Cable tray installation",
        action="installation",
        location="Rack B",
        event_date=date(2026, 9, 10),
    )


def _activities() -> list[ScheduleActivityCandidate]:
    return [
        ScheduleActivityCandidate(
            activity_id="ELE-101",
            discipline="Electrical",
            description="Install cable tray at Rack B",
            area="Rack B",
            planned_start=date(2026, 9, 8),
            planned_finish=date(2026, 9, 12),
        ),
        ScheduleActivityCandidate(
            activity_id="ELE-102",
            discipline="Electrical",
            description="Install conduit at Unit 3",
            area="Unit 3",
            planned_start=date(2026, 9, 8),
            planned_finish=date(2026, 9, 12),
        ),
        ScheduleActivityCandidate(
            activity_id="PIP-101",
            discipline="Piping",
            description="Erect Line 24-XX at Rack B",
            area="Rack B",
            planned_start=date(2026, 9, 8),
            planned_finish=date(2026, 9, 12),
        ),
    ]


def _patch_embedding_repository(monkeypatch, top_k_result: list[tuple[str, float]]):
    """Stubs out the three embedding_repository functions find_matches calls,
    so no real DB/pgvector is touched. Returns a call recorder dict."""
    calls: dict[str, Any] = {"saved": None, "top_k_args": None}

    def fake_get_cached_activity_ids(db, project_id):
        return set()  # nothing cached — forces the "compute + save" path

    def fake_save_embeddings(db, project_id, embeddings):
        calls["saved"] = embeddings

    def fake_top_k_similar(db, project_id, query_embedding, candidate_activity_ids, k):
        calls["top_k_args"] = candidate_activity_ids
        return top_k_result

    monkeypatch.setattr(embedding_repository, "get_cached_activity_ids", fake_get_cached_activity_ids)
    monkeypatch.setattr(embedding_repository, "save_embeddings", fake_save_embeddings)
    monkeypatch.setattr(embedding_repository, "top_k_similar", fake_top_k_similar)
    return calls


def test_find_matches_excludes_wrong_discipline_from_retrieval(monkeypatch):
    """The Piping candidate must never reach embeddings/retrieval at all —
    proves hard_filter runs before semantic retrieval, not after."""
    calls = _patch_embedding_repository(
        monkeypatch, top_k_result=[("ELE-101", 0.9), ("ELE-102", 0.4)]
    )
    llm = FakeLLMProvider(rankings=[{"candidate_activity_id": "ELE-101", "score": 0.9, "reasons": ["match"]}])

    find_matches(db=None, project_id="proj-1", event=_event(), activities=_activities(),
                 embeddings_provider=FakeEmbeddingsProvider(), llm_provider=llm)

    assert "PIP-101" not in calls["top_k_args"]
    assert set(calls["top_k_args"]) == {"ELE-101", "ELE-102"}


def test_find_matches_returns_empty_list_when_no_candidates_survive_hard_filter(monkeypatch):
    calls = _patch_embedding_repository(monkeypatch, top_k_result=[])
    event = MatchInput(
        event_id="EVT-1", discipline="Instrumentation", activity_description="x",
        action="x", location="x", event_date=date(2026, 9, 10),
    )

    matches = find_matches(db=None, project_id="proj-1", event=event, activities=_activities(),
                            embeddings_provider=FakeEmbeddingsProvider(), llm_provider=FakeLLMProvider())

    assert matches == []
    assert calls["top_k_args"] is None  # never even reached the retrieval stage


def test_find_matches_sorts_by_confidence_descending(monkeypatch):
    _patch_embedding_repository(monkeypatch, top_k_result=[("ELE-101", 0.95), ("ELE-102", 0.3)])
    llm = FakeLLMProvider(rankings=[
        {"candidate_activity_id": "ELE-101", "score": 0.9, "reasons": ["strong match"]},
        {"candidate_activity_id": "ELE-102", "score": 0.1, "reasons": ["weak match"]},
    ])

    matches = find_matches(db=None, project_id="proj-1", event=_event(), activities=_activities(),
                            embeddings_provider=FakeEmbeddingsProvider(), llm_provider=llm)

    assert [m.candidate_activity_id for m in matches] == ["ELE-101", "ELE-102"]
    assert matches[0].final_confidence >= matches[1].final_confidence


def test_find_matches_output_includes_terminology_score(monkeypatch):
    """Proves the field propagates through the full orchestration path
    (matching_service.find_matches -> MatchRecord), not just in the
    lower-level score_candidate unit tests."""
    _patch_embedding_repository(monkeypatch, top_k_result=[("ELE-101", 0.9)])
    llm = FakeLLMProvider(rankings=[{"candidate_activity_id": "ELE-101", "score": 0.9, "reasons": []}])

    matches = find_matches(db=None, project_id="proj-1", event=_event(), activities=_activities(),
                            embeddings_provider=FakeEmbeddingsProvider(), llm_provider=llm)

    assert hasattr(matches[0], "terminology_score")
    assert 0.0 <= matches[0].terminology_score <= 1.0


def test_find_matches_llm_score_zero_when_reranking_unavailable_not_fabricated(monkeypatch):
    """If reranking fails entirely, llm_score must be 0 for every candidate —
    never a fabricated/guessed score standing in for a real LLM signal."""
    _patch_embedding_repository(monkeypatch, top_k_result=[("ELE-101", 0.8)])
    llm = FakeLLMProvider(raises=LLMExtractionError("both providers failed"))

    matches = find_matches(db=None, project_id="proj-1", event=_event(), activities=_activities(),
                            embeddings_provider=FakeEmbeddingsProvider(), llm_provider=llm)

    assert len(matches) == 1
    assert matches[0].llm_score == 0.0


def test_find_matches_computes_embeddings_only_for_uncached_activities(monkeypatch):
    calls = _patch_embedding_repository(monkeypatch, top_k_result=[("ELE-101", 0.8), ("ELE-102", 0.5)])

    find_matches(db=None, project_id="proj-1", event=_event(), activities=_activities(),
                 embeddings_provider=FakeEmbeddingsProvider(), llm_provider=FakeLLMProvider())

    # Both Electrical candidates were "uncached" (fake returns empty set), so
    # both should have been embedded and saved.
    assert set(calls["saved"].keys()) == {"ELE-101", "ELE-102"}


def test_find_matches_decision_field_is_a_valid_match_decision(monkeypatch):
    _patch_embedding_repository(monkeypatch, top_k_result=[("ELE-101", 0.9)])
    llm = FakeLLMProvider(rankings=[{"candidate_activity_id": "ELE-101", "score": 0.9, "reasons": []}])

    matches = find_matches(db=None, project_id="proj-1", event=_event(), activities=_activities(),
                            embeddings_provider=FakeEmbeddingsProvider(), llm_provider=llm)

    assert matches[0].decision in (MatchDecision.AUTO_MATCH, MatchDecision.REVIEW_REQUIRED, MatchDecision.UNMATCHED)
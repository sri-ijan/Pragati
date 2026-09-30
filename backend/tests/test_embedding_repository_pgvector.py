"""
Tests embedding_repository.top_k_similar against a REAL Postgres + pgvector
instance (the actual SQL cosine-distance query, not a mock) — this is the one
piece of Slice 4 that genuinely cannot be verified on SQLite, since pgvector's
`<=>` operator is Postgres-specific.

Skips itself cleanly if DATABASE_URL isn't reachable or the vector extension
isn't installed, so the rest of the suite still runs fully on machines without
a local Postgres — this file being skipped does not mean Slice 4 is
unverified, just that this one DB-specific piece needs a real Postgres to
check directly (see test_matching_orchestration.py for the
mocked-repository version that runs everywhere).
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from config.database import engine
from models.orm import Base
from repositories import embedding_repository


def _pgvector_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pgvector_available(),
    reason="Postgres with the pgvector extension is not reachable — set DATABASE_URL "
    "to a real Postgres instance with pgvector installed to run this test.",
)


@pytest.fixture()
def pg_session():
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    session.execute(
        text(
            "INSERT INTO projects (project_id, name, created_at) VALUES "
            "('test-pgvector-proj', 'pgvector test project', now()) "
            "ON CONFLICT (project_id) DO NOTHING"
        )
    )
    session.commit()
    try:
        yield session
    finally:
        # Clean up rows this test created, leave the schema itself alone.
        session.rollback()
        session.execute(text("DELETE FROM activity_embeddings WHERE project_id = 'test-pgvector-proj'"))
        session.execute(text("DELETE FROM projects WHERE project_id = 'test-pgvector-proj'"))
        session.commit()
        session.close()


def test_top_k_similar_orders_by_actual_cosine_distance(pg_session):
    # Three simple, clearly-distinguishable vectors in a small dimensionality
    # subspace padded to EMBEDDING_DIMENSIONS with zeros — exact values don't
    # matter, only that pgvector correctly orders by real cosine distance.
    from services.embeddings_provider import EMBEDDING_DIMENSIONS

    def vec(x: float, y: float) -> list[float]:
        return [x, y] + [0.0] * (EMBEDDING_DIMENSIONS - 2)

    embedding_repository.save_embeddings(
        pg_session,
        "test-pgvector-proj",
        {
            "CLOSE": vec(1.0, 0.0),
            "FAR": vec(0.0, 1.0),
            "OPPOSITE": vec(-1.0, 0.0),
        },
    )

    query = vec(0.9, 0.1)  # nearly identical direction to "CLOSE"
    results = embedding_repository.top_k_similar(
        pg_session, "test-pgvector-proj", query, ["CLOSE", "FAR", "OPPOSITE"], k=3
    )

    ordered_ids = [activity_id for activity_id, _ in results]
    assert ordered_ids[0] == "CLOSE"
    assert ordered_ids[-1] == "OPPOSITE"
    # Similarity to itself-ish direction should be high, to the opposite
    # direction should be low/negative-clamped.
    assert dict(results)["CLOSE"] > dict(results)["OPPOSITE"]


def test_top_k_similar_respects_the_candidate_id_filter(pg_session):
    from services.embeddings_provider import EMBEDDING_DIMENSIONS

    def vec(x: float) -> list[float]:
        return [x] + [0.0] * (EMBEDDING_DIMENSIONS - 1)

    embedding_repository.save_embeddings(
        pg_session,
        "test-pgvector-proj",
        {"IN_SET": vec(1.0), "EXCLUDED": vec(1.0)},
    )

    results = embedding_repository.top_k_similar(
        pg_session, "test-pgvector-proj", vec(1.0), ["IN_SET"], k=5
    )

    assert [activity_id for activity_id, _ in results] == ["IN_SET"]
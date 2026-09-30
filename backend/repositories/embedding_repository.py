"""
SetuAI — Activity Embedding Repository (Slice 4)

Caches schedule-activity embeddings in Postgres (pgvector) so they're
computed once per activity, not on every match request, and runs the actual
semantic retrieval as a real pgvector cosine-distance SQL query rather than
pulling every embedding into Python and comparing there.

Cache invalidation is NOT implemented: if a schedule activity's description
changes (e.g. a corrected re-upload), its cached embedding goes stale until
something explicitly recomputes it. Flagged as a known simplification in
docs/DECISIONS.md, not silently glossed over.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.orm import ActivityEmbeddingORM


def get_cached_activity_ids(db: Session, project_id: str) -> set[str]:
    return set(
        db.execute(
            select(ActivityEmbeddingORM.activity_id).where(
                ActivityEmbeddingORM.project_id == project_id
            )
        ).scalars()
    )


def save_embeddings(db: Session, project_id: str, embeddings: dict[str, list[float]]) -> None:
    for activity_id, vector in embeddings.items():
        db.add(
            ActivityEmbeddingORM(
                project_id=project_id,
                activity_id=activity_id,
                embedding=vector,
            )
        )
    db.commit()


def top_k_similar(
    db: Session,
    project_id: str,
    query_embedding: list[float],
    candidate_activity_ids: list[str],
    k: int,
) -> list[tuple[str, float]]:
    """Real pgvector query: cosine distance between query_embedding and every
    cached embedding for the given (already hard-filtered) candidate activity
    IDs, ordered nearest-first, limited to k. Returns (activity_id,
    similarity) where similarity = 1 - cosine_distance, clamped to [0, 1]."""
    if not candidate_activity_ids:
        return []

    distance = ActivityEmbeddingORM.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(ActivityEmbeddingORM.activity_id, distance)
        .where(ActivityEmbeddingORM.project_id == project_id)
        .where(ActivityEmbeddingORM.activity_id.in_(candidate_activity_ids))
        .order_by(distance)
        .limit(k)
    )
    rows = db.execute(stmt).all()
    return [(activity_id, max(0.0, min(1.0, 1.0 - dist))) for activity_id, dist in rows]
"""
SetuAI — Match Repository (Slice 4)

DB access for `activity_matches` only. A fresh POST /events/{id}/match run
REPLACES the previous batch of candidates for that event_id (delete + insert)
rather than accumulating history — see models/orm.ActivityMatchORM's
docstring for why.
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.orm import ActivityMatchORM
from models.schemas import MatchRecord


def replace_matches(db: Session, event_id: str, matches: list[MatchRecord]) -> None:
    db.execute(delete(ActivityMatchORM).where(ActivityMatchORM.event_id == event_id))
    for match in matches:
        db.add(
            ActivityMatchORM(
                event_id=event_id,  # the function's own parameter, not match.event_id —
                # avoids silently misfiling a row if the two ever disagree.
                candidate_activity_id=match.candidate_activity_id,
                semantic_score=match.semantic_score,
                metadata_score=match.metadata_score,
                temporal_score=match.temporal_score,
                llm_score=match.llm_score,
                terminology_score=match.terminology_score,
                final_confidence=match.final_confidence,
                decision=match.decision.value,
                reviewer=match.reviewer,
                reason=match.reason,
            )
        )
    db.commit()


def get_matches_for_event(db: Session, event_id: str) -> list[ActivityMatchORM]:
    return list(
        db.execute(
            select(ActivityMatchORM)
            .where(ActivityMatchORM.event_id == event_id)
            .order_by(ActivityMatchORM.final_confidence.desc())
        ).scalars()
    )
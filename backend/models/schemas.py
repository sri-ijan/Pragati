"""
SetuAI — Shared Contracts (Pydantic)

Source of truth: plan.md §6, §22 + docs/API.md. Mirrored 1:1 in
shared/types.ts — if you change a field here, change it there too, and log
the change in docs/DECISIONS.md.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Discipline(str, Enum):
    CIVIL = "Civil"
    PIPING = "Piping"
    ELECTRICAL = "Electrical"
    INSTRUMENTATION = "Instrumentation"


class EventStatus(str, Enum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    HOLD = "hold"
    CANCELLED = "cancelled"


class MatchDecision(str, Enum):
    AUTO_MATCH = "auto_match"
    REVIEW_REQUIRED = "review_required"
    UNMATCHED = "unmatched"


class ReviewAction(str, Enum):
    APPROVE = "approve"
    CORRECT = "correct"
    REJECT = "reject"


# ---------------------------------------------------------------------------
# Canonical domain schemas (plan.md §6)
# ---------------------------------------------------------------------------

class ExecutionEvent(BaseModel):
    event_id: str
    source_id: str
    discipline: Discipline
    activity_description: str
    action: str
    status: EventStatus
    location: str
    equipment_tag: Optional[str] = None
    line_number: Optional[str] = None
    event_date: date
    quantity: Optional[float] = None
    unit: Optional[str] = None
    raw_text: str
    confidence: Optional[float] = None  # null until matched


class ScheduleActivity(BaseModel):
    activity_id: str
    wbs: str
    discipline: Discipline
    description: str
    area: str
    planned_start: date
    planned_finish: date
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None


class MatchRecord(BaseModel):
    event_id: str
    candidate_activity_id: str
    semantic_score: float = Field(ge=0, le=1)
    metadata_score: float = Field(ge=0, le=1)
    temporal_score: float = Field(ge=0, le=1)
    llm_score: float = Field(ge=0, le=1)
    final_confidence: float = Field(ge=0, le=1)
    decision: MatchDecision
    reviewer: Optional[str] = None
    reason: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Confidence formula (plan.md §11) — keep this the single implementation.
# Weights are prototype values, configurable, not scientifically validated.
# ---------------------------------------------------------------------------

CONFIDENCE_WEIGHTS = {
    "semantic": 0.35,
    "metadata": 0.25,
    "llm_rerank": 0.20,
    "temporal": 0.10,
    "terminology": 0.10,
}

CONFIDENCE_THRESHOLDS = {
    "auto_match": 0.90,
    "review_required": 0.70,  # >= this and < auto_match threshold
}


def decision_for_confidence(score: float) -> MatchDecision:
    if score >= CONFIDENCE_THRESHOLDS["auto_match"]:
        return MatchDecision.AUTO_MATCH
    if score >= CONFIDENCE_THRESHOLDS["review_required"]:
        return MatchDecision.REVIEW_REQUIRED
    return MatchDecision.UNMATCHED


# ---------------------------------------------------------------------------
# API envelope
# ---------------------------------------------------------------------------

class ApiErrorDetail(BaseModel):
    code: str  # e.g. "SCHEDULE_PARSE_ERROR", "NOT_FOUND", "VALIDATION_ERROR"
    message: str
    details: Optional[dict] = None


class ApiError(BaseModel):
    error: ApiErrorDetail


class Project(BaseModel):
    project_id: str
    name: str
    created_at: datetime


class AuditLogEntry(BaseModel):
    audit_id: str
    event_id: str
    source_document_id: str
    field: str  # "actual_start" | "actual_finish"
    before: Optional[date] = None
    after: date
    decision: MatchDecision
    reviewer: Optional[str] = None
    confidence: float
    timestamp: datetime


# ---------------------------------------------------------------------------
# Endpoint request/response shapes — see docs/API.md for the full endpoint list
# ---------------------------------------------------------------------------

class UploadScheduleResponse(BaseModel):
    project_id: str
    activities_imported: int
    warnings: list[str] = Field(default_factory=list)


class UploadDocumentResponse(BaseModel):
    source_document_id: str
    filename: str
    status: str  # "received" | "extraction_pending"


class ExtractResponse(BaseModel):
    events: list[ExecutionEvent]


class MatchResponse(BaseModel):
    event_id: str
    candidates: list[MatchRecord]  # sorted by final_confidence desc


class ReviewDecisionRequest(BaseModel):
    action: ReviewAction
    corrected_activity_id: Optional[str] = None  # required when action == correct
    reviewer: str


class AnalyticsSummary(BaseModel):
    total_activities: int
    actualized_activities: int
    auto_matched_pct: float
    review_pct: float
    unmatched_pct: float
    average_confidence: float
    delayed_count: int
    on_time_count: int
    early_count: int

/**
 * SetuAI — Shared Contracts (TypeScript)
 *
 * Source of truth: plan.md §6, §22 + docs/API.md. Mirrored 1:1 in
 * backend/models/schemas.py — if you change a field here, change it there too,
 * and log the change in docs/DECISIONS.md.
 *
 * Field naming stays snake_case to match the JSON wire format exactly (no
 * camelCase remapping) — one less place for a bug to hide.
 */

export type Discipline = "Civil" | "Piping" | "Electrical" | "Instrumentation";

export type EventStatus =
  | "started"
  | "in_progress"
  | "completed"
  | "hold"
  | "cancelled";

export type MatchDecision = "auto_match" | "review_required" | "unmatched";

export type ReviewAction = "approve" | "correct" | "reject";

// ---------------------------------------------------------------------------
// Canonical domain schemas (plan.md §6)
// ---------------------------------------------------------------------------

export interface ExecutionEvent {
  event_id: string;
  source_id: string;
  discipline: Discipline;
  activity_description: string;
  action: string;
  status: EventStatus;
  location: string;
  equipment_tag: string | null;
  line_number: string | null;
  event_date: string; // ISO-8601 date, e.g. "2026-09-08"
  quantity: number | null;
  unit: string | null;
  raw_text: string;
  confidence: number | null; // null until matched
}

export interface ScheduleActivity {
  activity_id: string;
  wbs: string;
  discipline: Discipline;
  description: string;
  area: string;
  planned_start: string; // ISO-8601 date
  planned_finish: string; // ISO-8601 date
  actual_start: string | null;
  actual_finish: string | null;
}

export interface MatchRecord {
  event_id: string;
  candidate_activity_id: string;
  semantic_score: number; // 0..1
  metadata_score: number; // 0..1
  temporal_score: number; // 0..1
  llm_score: number; // 0..1
  terminology_score: number; // 0..1
  final_confidence: number; // 0..1, weighted composite — see computeConfidence below
  decision: MatchDecision;
  reviewer: string | null;
  reason: string[]; // short human-readable factors, e.g. "Same discipline"
}

// ---------------------------------------------------------------------------
// Confidence formula (plan.md §11) — keep this the single implementation.
// Weights are prototype values, configurable, not scientifically validated.
// ---------------------------------------------------------------------------

export const CONFIDENCE_WEIGHTS = {
  semantic: 0.35,
  metadata: 0.25,
  llm_rerank: 0.20,
  temporal: 0.10,
  terminology: 0.10,
} as const;

export const CONFIDENCE_THRESHOLDS = {
  auto_match: 0.90,
  review_required: 0.70, // >= this and < auto_match threshold
} as const;

export function decisionForConfidence(score: number): MatchDecision {
  if (score >= CONFIDENCE_THRESHOLDS.auto_match) return "auto_match";
  if (score >= CONFIDENCE_THRESHOLDS.review_required) return "review_required";
  return "unmatched";
}

// ---------------------------------------------------------------------------
// API envelope
// ---------------------------------------------------------------------------

export interface ApiError {
  error: {
    code: string; // e.g. "SCHEDULE_PARSE_ERROR", "NOT_FOUND", "VALIDATION_ERROR"
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface Project {
  project_id: string;
  name: string;
  created_at: string; // ISO-8601 datetime
}

export interface AuditLogEntry {
  audit_id: string;
  event_id: string;
  source_document_id: string;
  field: "actual_start" | "actual_finish";
  before: string | null;
  after: string;
  decision: MatchDecision;
  reviewer: string | null;
  confidence: number;
  timestamp: string; // ISO-8601 datetime
}

// ---------------------------------------------------------------------------
// Endpoint request/response shapes — see docs/API.md for the full endpoint list
// ---------------------------------------------------------------------------

export interface UploadScheduleResponse {
  project_id: string;
  activities_imported: number;
  warnings: string[]; // e.g. rows skipped for missing required columns
}

export interface UploadDocumentResponse {
  source_document_id: string;
  filename: string;
  status: "received" | "extraction_pending";
}

export interface ExtractResponse {
  events: ExecutionEvent[];
}

export interface MatchResponse {
  event_id: string;
  candidates: MatchRecord[]; // sorted by final_confidence desc, top-3 minimum shown in UI
}

export interface ReviewDecisionRequest {
  action: ReviewAction;
  corrected_activity_id?: string; // required when action === "correct"
  reviewer: string;
}

export interface AnalyticsSummary {
  total_activities: number;
  actualized_activities: number;
  auto_matched_pct: number;
  review_pct: number;
  unmatched_pct: number;
  average_confidence: number;
  delayed_count: number;
  on_time_count: number;
  early_count: number;
}
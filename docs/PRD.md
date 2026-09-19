# SetuAI — Product Requirements Document

Source of truth for product substance: `plan.md`. This document restates it in PRD form; it does
not re-derive or simplify it.

## Problem

Infrastructure projects maintain a structured baseline schedule (Primavera P6 / MS Project,
L5/L6 activity level), but actual execution data arrives through DPRs, spreadsheets, site diaries,
scanned documents, and verbal updates — in inconsistent terminology and granularity. Reliably
mapping field progress back to schedule activities today requires manual reconciliation.

## Target Users

- **Planners** — own the baseline schedule, need trustworthy actuals without manual reconciliation.
- **Site supervisors** — file DPRs/updates in their own natural language, don't want to learn a new
  reporting system.
- **Project controls / PMO** — need auditability and confidence that automated updates are safe.

## User Pain Points

- Terminology drift between planning language ("Erect Line 24-XX at Rack B") and field language
  ("24-inch spool erected at Rack B").
- Granularity mismatch — one field report can cover multiple schedule activities, or vice versa.
- Missing activity IDs in field reports.
- No reliable, auditable trail from "what was reported" to "what got updated in the schedule."
- Existing broad platforms (Procore, Autodesk Construction Cloud, Oracle Aconex, Bentley SYNCHRO)
  address field reporting and project controls generally, but not this specific reconciliation gap.

## MVP Objective

Build a working, demoable AI Planning-to-Execution Bridge that ingests 2–3 field input formats,
extracts structured execution events, matches them to L5/L6 schedule activities through a hybrid
metadata + semantic + LLM + rules pipeline, assigns a defensible confidence score, routes ambiguous
cases to human review, and updates the schedule with a full audit trail — end to end, on a
full-scale synthetic dataset, not a single cherry-picked example.

## Core User Journey

```text
Planner uploads schedule → parsed
Supervisor uploads DPR/spreadsheet → AI extracts execution events → normalized
Candidate L5/L6 activities retrieved → matching engine scores candidates
  High confidence → auto-match
  Medium confidence → planner review
  Low confidence → unmatched queue
Planner approves/corrects → actual start/end updated → audit trail created
→ analytics + project memory updated
```

## Features (Priority per `plan.md` §36)

| Feature | Priority | Build? |
|---|---|---|
| Schedule ingestion (Excel) | P0 | Yes |
| DPR ingestion (PDF/text) | P0 | Yes |
| Structured extraction (LLM, schema-constrained) | P0 | Yes |
| Semantic matching (hybrid pipeline) | P0 | Yes |
| Confidence scoring | P0 | Yes |
| Review queue (approve/correct/unmatched) | P0 | Yes |
| Schedule update (actual dates) | P0 | Yes |
| Audit trail | P0 | Yes |
| Analytics dashboard | P1 | Yes |
| Historical/institutional memory | P1 | Yes |
| Voice interface | P2 | Only if time remains |
| OCR | P2 | Optional |
| Real Primavera/PMIS integration | P2 | Mock/API boundary only — never faked as live |
| Delay forecasting | P3 | Optional |
| Computer vision, blockchain, AR/VR | P3 | No |

Do not implement P1/P2 features while P0 is incomplete (Master Prompt §6).

## Functional Requirements

- Parse a schedule Excel file into structured activities (Activity ID, WBS, description, discipline,
  area, planned start/finish, optional tags/line/equipment IDs); store original + normalized rows.
- Accept field updates as free text, PDF/DPR upload, or spreadsheet; normalize varying column names
  (e.g. "Work Description"/"Activity"/"Job Description" → `activity_description`).
- Extract structured execution events via schema-constrained LLM output only — never free-form;
  never invent an activity ID; never infer a date unsupported by the source; preserve raw evidence.
- Normalize discipline-specific terminology via a growing dictionary (seeded, then expanded from
  reviewer corrections).
- Run the four-stage matching pipeline (hard filter → semantic retrieval → LLM rerank →
  deterministic validation) — see `docs/ARCHITECTURE.md`.
- Compute a weighted composite confidence score (semantic/metadata/LLM-rerank/temporal/terminology)
  and route by threshold (≥0.90 auto-match, 0.70–0.89 review, <0.70 unmatched).
- Provide a reviewer screen: field event, top candidates with %, explainability checklist,
  Approve/Correct/Unmatched actions.
- On approval, update `actual_start`/`actual_finish` in the schedule store and write a full audit
  record (source, evidence location, extracted data, candidates, scores, decision, reviewer,
  before/after values, timestamp).
- Provide an analytics dashboard (total activities, actualized %, auto-matched/review/unmatched %,
  average confidence, delayed/early/on-time counts).
- Store validated events as institutional memory queryable in natural language.

## Non-Functional Requirements

- Human-in-the-loop by design: no uncertain AI prediction may silently modify schedule data.
- Explainability: every match must show *why* it won, not just a confidence number.
- Auditability: every schedule-affecting decision must be traceable end to end.
- Confidence weights/thresholds are prototype values, configurable, and explicitly not claimed as
  scientifically validated — say so if asked.
- Integration posture: treat the uploaded schedule as system of record; expose an integration-ready
  API boundary; never fake a live Primavera/PMIS connection.

## Success Criteria

Benchmark targets on the ~150-field-event synthetic dataset (`plan.md` §20 — internal prototype
targets, not production claims):

```text
Top-1 correct match:        >= 85%
Top-3 candidate recall:     >= 95%
High-confidence precision:  >= 95%
False auto-match rate:      <= 5%
Extraction accuracy:        >= 90%
```

High-confidence precision matters most: it's better to send an ambiguous event to a human than to
confidently update the wrong activity.

## Demo Scenario

See `context.md` §19 ("Demo Flow") and `plan.md` §33 ("Killer Demo") — the exact 9-step sequence to
rehearse. Must be ready to show top-3 matches (not just the winner) on judge request (`plan.md` §30).

## Non-Goals

Per `plan.md` §1: no full Primavera replacement, no production-grade OCR/ASR, no full construction
ERP/PMIS, no computer vision from site cameras, no drone/BIM/digital-twin platform, no autonomous
schedule replanning, no production-grade delay forecasting, no enterprise identity/security, no
nationwide deployment. The core problem is field evidence → L5/L6 semantic reconciliation — nothing
broader.

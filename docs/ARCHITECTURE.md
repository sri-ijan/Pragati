# SetuAI — Architecture

Source of truth: `plan.md` §4, §5, §10, §28. This document restates it; it does not re-derive it.

## Architecture Principle

Prefer deterministic software + AI where AI is actually useful. Do not build "LLM does everything."

```text
LLM            → language understanding, entity extraction, reasoning over a small candidate set
Embeddings     → semantic retrieval
Rules          → hard constraints, validation
Humans         → ambiguity resolution
Database       → source of truth
```

Avoid the naive architecture `DPR → LLM → Activity ID → automatic schedule update`. A hallucinated
match can corrupt project controls; this is the biggest defensibility risk in the whole project
(`plan.md` §28, §31).

## System Diagram

```text
                        ┌──────────────────────┐
                        │   Web Application     │
                        │ React / Next.js       │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │      FastAPI         │
                        │      Backend         │
                        └──────────┬───────────┘
                                   │
             ┌─────────────────────┼──────────────────────┐
             ▼                     ▼                      ▼
      File Ingestion          AI Extraction          Schedule API
             │                     │                      │
      PDF / Excel / Text     LLM → JSON             Schedule Data
             │                     │                      │
             └─────────────────────┼──────────────────────┘
                                   ▼
                         Canonical Event Model
                                   │
                                   ▼
                    ┌─────────────────────────┐
                    │ Candidate Retrieval     │
                    │ Metadata + Vector DB    │
                    └────────────┬────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │ Matching / Reranking    │
                    │ Embeddings + LLM + Rules│
                    └────────────┬────────────┘
                                 ▼
                         Confidence Engine
                                 │
                 ┌───────────────┼────────────────┐
                 ▼               ▼                ▼
              AUTO             REVIEW          UNMATCHED
             MATCH              QUEUE             QUEUE
                 │               │                │
                 └───────────────┼────────────────┘
                                 ▼
                        Schedule / PMIS Store
                                 │
                 ┌───────────────┴────────────────┐
                 ▼                                ▼
           Live Analytics                  Project Memory
```

## Tech Stack

**Frontend:** React / Next.js, Tailwind CSS, Recharts or ECharts. Voice recording UI is optional
and deferred (Phase 9, only if the core pipeline is stable).

**Backend:** Python, FastAPI, Pydantic.

**Data processing:** Pandas, openpyxl (Excel), PyMuPDF or pdfplumber (PDF); OCR only if a real need
appears — not built speculatively.

**AI:** LLM for structured extraction and candidate reasoning; embeddings for semantic retrieval;
an optional small classifier/reranker only if enough labelled examples exist to train one.

**Database:** PostgreSQL with pgvector for embedding storage/similarity search.

**Deployment (hackathon-grade):** Frontend on a Vercel-equivalent host, backend on a
Render/Railway/equivalent host, database on a hosted Postgres service. Avoid spending time on
complex infrastructure — this is explicitly deprioritized relative to the matching engine.

## Matching Engine (the technical centerpiece)

Four stages, run in order, on every execution event:

**Stage 1 — Hard filtering.** Reduce the candidate set using discipline, area, WBS, line number,
equipment tag, date, and activity status. E.g. a Piping event immediately excludes all
Civil/Electrical activities, then non-matching areas, then non-matching line numbers.

**Stage 2 — Semantic retrieval.** Generate embeddings for the field event and for schedule activity
descriptions; retrieve top-K candidates by vector similarity. Recommended K: 5–10.

**Stage 3 — LLM reranking.** Give the LLM only the filtered candidate set (never the full schedule)
and ask it to evaluate action, object, location, discipline, tags, temporal compatibility, and
granularity.

**Stage 4 — Deterministic validation.** Reject or penalize impossible matches: discipline mismatch,
explicit line-number mismatch, a completion event against an already-completed incompatible
activity, an event date outside a reasonable window, or a category-wrong match (e.g. a hydrotest
event mapped to an erection activity).

Do not simplify this to keyword-only matching, and do not skip stages to save time — see
`context.md` §10 for the confidence formula that consumes these stage outputs, and §12/§31 for why
this specific risk gets the most engineering time of anything in the project.

## Data Layer

Minimum tables (`plan.md` §23): `projects`, `schedule_activities`, `source_documents`,
`execution_events`, `activity_matches`, `review_decisions`, `audit_logs`, `terminology`,
`historical_activity_stats`. Optional: `activity_embeddings`, `contractors`, `delay_causes`.

Canonical schemas (Execution Event, Schedule Activity, Match Record) are fixed in `plan.md` §6 and
mirrored in `context.md` §8 — do not redesign them independently; extend only with team agreement,
logged in `docs/DECISIONS.md`.

## Repository Layout

See `context.md` §6 for the target directory structure. Each of the six parallel tracks
(`docs/ROADMAP.md`) owns a mostly-separate subtree, which is why this layout matters for
coordination, not just tidiness.

## Integration Boundary

The MVP treats the uploaded schedule as the system of record. It does not integrate with a live
Primavera/PMIS instance. It demonstrates an integration-ready API boundary instead, and states
plainly (including to judges) that production deployment would connect through supported
Primavera/PMIS APIs — never fake a live integration (`plan.md` §14, §29 Q4).

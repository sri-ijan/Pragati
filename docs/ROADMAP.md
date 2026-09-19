# SetuAI — Roadmap

Source of truth: `plan.md` §24–§26; process wrapper: Master Engineering Prompt §7, §23.

## Slice 0 — Shared Contracts (blocking, done together)

Before anyone parallelizes: agree on repository structure, shared data models/types (Execution
Event, Schedule Activity, Match Record, Confidence Score), API contract shapes, and naming
conventions. Write results into `context.md` §8/§9 and `docs/API.md`. **Budget: ~1–2 hrs.**
Parallel work that starts before this is done reliably produces integration disasters later that
cost far more than this sitting does.

## Development Phases (per `plan.md` §24, cross-referenced to the vertical-slice table below)

| Phase | Scope | Success condition |
|---|---|---|
| 1. Domain & Dataset | Synthetic project, schedule dataset, DPR dataset, terminology dictionary, ground truth. Do not start with UI. | Full dataset target met (see below) |
| 2. Basic Ingestion | Excel parser, PDF/text parser, canonical event schema, schedule database | All inputs become structured records |
| 3. AI Extraction | LLM extraction, validation, evidence preservation | DPR → structured execution event |
| 4. Matching Engine | Metadata filtering, embeddings, top-K retrieval, LLM reranking, rule validation | Field event → correct L5/L6 candidate. **Highest-priority phase.** |
| 5. Confidence + Review | Confidence scoring, review queue, approve/correct/unmatched | Ambiguous cases never silently auto-update |
| 6. Schedule Update | Actual start/end update, before/after comparison, audit record | Approved event changes schedule state |
| 7. Dashboard | Project summary, reconciliation metrics, schedule variance, discipline analytics | — |
| 8. Institutional Memory | Historical activity records, query interface, simple delay-pattern analytics | — |
| 9. Voice | Only if everything above is stable | — |

## Vertical Slices with Time Budgets (Master Prompt §23 — adjust to the phase plan above)

| Slice | Scope | Budget |
|---|---|---|
| 0 | Shared contracts, repo scaffolding, data models (blocking) | ~1–2 hrs |
| 1 | Schedule upload: UI → API → parser → database → UI result | ~2–3 hrs |
| 2 | Field report: UI → API → database → UI | ~1–2 hrs |
| 3 | AI extraction: field report → AI → validated JSON → UI | ~2–3 hrs |
| 4 | Matching: extraction → candidate retrieval → matching → confidence → UI | ~4–6 hrs (protect this time) |
| 5 | Approval: approve → backend → database → activity status → dashboard | ~2–3 hrs |
| (parallel) | Dataset generation | runs throughout |
| (parallel) | Pitch/demo prep, Q&A rehearsal | starts once Slice 3–4 are demo-stable |

## Hackathon Time Allocation (24–36 hr build, `plan.md` §25)

```text
0–3 hrs    Understand PS + finalize schema + create dataset
3–7 hrs    Backend + database + ingestion
7–12 hrs   LLM extraction + normalization
12–18 hrs  Matching engine
18–22 hrs  Confidence + review workflow
22–26 hrs  Dashboard + schedule update
26–30 hrs  Institutional memory + analytics
30–34 hrs  Testing + demo data + polish
final hrs  Pitch + judge Q&A + backup demo
```

If time gets short: cut voice before cutting matching / review / audit trail. Never simplify the
matching engine to save time (`plan.md` §18, §25).

## Parallel Tracks (Master Prompt §7C, once Slice 0 contracts exist)

| Track | Scope | Lead (flexible) |
|---|---|---|
| A | Schedule ingestion/parsing + database layer | Backend |
| B | Field report input + extraction (against agreed extraction schema) | AI/ML |
| C | Matching engine + confidence scoring — highest-risk track, gets extra people if anyone is filling in | AI/ML + Backend |
| D | Dataset generation, continuous, full scale (see below) | Data/Domain |
| E | Frontend/dashboard, built against mocked API responses until A–C are wired in | Frontend |
| F | Pitch materials, demo rehearsal, judge Q&A prep, can start early | Product/Pitch |

Coordination mechanism: `context.md` §14. Read it before starting a task; update it immediately
after finishing or pausing one.

## Team Responsibilities (`plan.md` §26 — roles are flexible; anyone may fill in for another)

- **AI/ML:** LLM extraction, embeddings, reranking, confidence logic.
- **Backend:** FastAPI, PostgreSQL, ingestion, APIs.
- **Frontend:** dashboard, matching screen, review workflow.
- **Data/Domain:** synthetic construction data, schedule structure, terminology, ground truth,
  evaluation.
- **Integration/Analytics:** schedule update, analytics, audit, deployment.
- **Product/Pitch:** UX, demo flow, presentation, documentation, judge Q&A.

## Dataset Target (Track D, runs throughout — `plan.md` §18)

At least: 300 schedule activities, 150 field events, 4 disciplines, 3 input formats, 30+ ambiguous
cases covering all 7 edge-case categories (easy, synonym, abbreviation, missing-ID, granularity
mismatch, ambiguous, negative/cross-discipline). Build via: bulk AI generation for the easy 80%,
human spot-check/hand-edit for the hard 20% (especially ambiguous/negative cases), ground-truth
every pair as it's generated, seed with 10–15 hand-written realistic activities across all 4
disciplines before AI-expanding at scale. Do not shrink this target to save time.

## Definition of Done (per feature, and for the MVP as a whole)

A feature is done when: implementation exists, frontend is connected, backend is connected,
database is connected where required, errors are handled, types/contracts are correct, relevant
tests pass, the manual flow works, `context.md` is updated, and — if a phase boundary was crossed —
the relevant `docs/` file is updated. Standard: if this is demoed live to a judge, it must actually
work. The MVP as a whole is done when a judge can complete the full loop in `plan.md` §37 without
anything breaking.

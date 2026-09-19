# SIH PS 122 --- AI-Powered Field-to-Schedule Reconciliation

## 0. Executive Summary

### Problem

Infrastructure projects have a structured baseline schedule in Primavera
P6 / MS Project, but actual execution data arrives through DPRs,
spreadsheets, site diaries, scanned documents, and verbal updates. These
sources use inconsistent terminology and granularity, making it
difficult to reliably map field progress back to L5/L6 schedule
activities.

### Product

Build an **AI Planning-to-Execution Bridge** that:

1.  Ingests heterogeneous field inputs.
2.  Extracts structured execution events.
3.  Normalizes discipline-specific terminology.
4.  Finds candidate L5/L6 schedule activities.
5.  Matches field events to schedule activities using metadata +
    semantic similarity + LLM reasoning + deterministic validation.
6.  Assigns confidence and routes ambiguous cases to human review.
7.  Updates a schedule/PMIS representation with an audit trail.
8.  Stores validated execution history as institutional memory.

### One-line pitch

> Convert how construction sites naturally report work into trustworthy,
> schedule-ready actuals without forcing supervisors to learn another
> reporting system.

------------------------------------------------------------------------

# 1. Goals and Non-Goals

## Goals

-   Demonstrate ingestion of at least 2--3 input formats.
-   Extract activity-level actual start/end/progress events.
-   Match field descriptions to L5/L6 schedule activities.
-   Handle terminology differences and granularity mismatch.
-   Provide confidence scores.
-   Provide a human-in-the-loop review workflow.
-   Show schedule actualization.
-   Maintain source evidence and audit history.
-   Demonstrate historical execution intelligence.

## Non-Goals for the Hackathon

Do not attempt to build:

-   A complete Primavera replacement.
-   Production-grade OCR/ASR.
-   Full construction ERP/PMIS.
-   Computer vision from site cameras.
-   Drone/BIM/digital-twin platform.
-   Autonomous schedule replanning.
-   Production-grade delay forecasting.
-   Enterprise-grade identity/security.
-   Nationwide deployment.

The core problem is **field evidence → L5/L6 semantic reconciliation**.

------------------------------------------------------------------------

# 2. Winning MVP

## Demo scenario

Use one synthetic infrastructure project containing:

-   Civil
-   Piping
-   Electrical
-   Instrumentation

Create:

-   `schedule.xlsx`
-   `daily_report.pdf` or `.txt`
-   `discipline_progress.xlsx`

Example schedule:

  --------------------------------------------------------------------------
  Activity ID Discipline   Description   Area        Planned     Planned
                                                     Start       Finish
  ----------- ------------ ------------- ----------- ----------- -----------
  PIP-101     Piping       Erect Line    Rack B      01-Sep      04-Sep
                           24-XX at Rack                         
                           B                                     

  PIP-102     Piping       Weld Line     Rack B      04-Sep      06-Sep
                           24-XX at Rack                         
                           B                                     

  CIV-201     Civil        Foundation    Unit 2      01-Sep      05-Sep
                           F-104                                 
  --------------------------------------------------------------------------

Example field report:

> "Piping crew completed erection of 24-inch spool at Rack B today."

System output:

``` json
{
  "discipline": "Piping",
  "event_type": "completion",
  "activity_description": "24-inch spool erection",
  "location": "Rack B",
  "event_date": "2026-09-08",
  "candidate_activity": "PIP-101",
  "confidence": 0.94,
  "decision": "auto_match"
}
```

------------------------------------------------------------------------

# 3. Core User Journey

``` text
Planner uploads schedule
        ↓
Schedule is parsed
        ↓
Supervisor uploads DPR / spreadsheet
        ↓
AI extracts execution events
        ↓
Events are normalized
        ↓
Candidate L5/L6 activities retrieved
        ↓
Matching engine scores candidates
        ↓
High-confidence → auto-match
Medium-confidence → planner review
Low-confidence → unmatched queue
        ↓
Planner approves/corrects
        ↓
Actual start/end is updated
        ↓
Audit trail created
        ↓
Analytics + project memory updated
```

------------------------------------------------------------------------

# 4. System Architecture

``` text
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

------------------------------------------------------------------------

# 5. Recommended Tech Stack

## Frontend

-   React / Next.js
-   Tailwind CSS
-   Recharts or ECharts
-   Optional: voice recording UI

## Backend

-   Python
-   FastAPI
-   Pydantic

## Data Processing

-   Pandas
-   openpyxl
-   PyMuPDF / pdfplumber
-   OCR only if needed

## AI

-   LLM for structured extraction and candidate reasoning.
-   Embeddings for semantic retrieval.
-   Optional small classifier/reranker if enough labelled examples
    exist.

## Database

-   PostgreSQL
-   pgvector for embeddings

## Deployment

For a hackathon: - Frontend: Vercel or equivalent - Backend:
Render/Railway/AWS/Azure equivalent - Database: PostgreSQL hosted
service

Avoid spending time on complex infrastructure.

------------------------------------------------------------------------

# 6. Canonical Data Model

Everything entering the system should be converted into a common schema.

## Execution Event

``` json
{
  "event_id": "EVT-001",
  "source_id": "DPR-2026-09-08-01",
  "discipline": "Piping",
  "activity_description": "24-inch spool erection",
  "action": "erection",
  "status": "completed",
  "location": "Rack B",
  "equipment_tag": null,
  "line_number": "24-XX",
  "event_date": "2026-09-08",
  "quantity": null,
  "unit": null,
  "raw_text": "Piping crew completed erection...",
  "confidence": null
}
```

## Schedule Activity

``` json
{
  "activity_id": "PIP-101",
  "wbs": "PIP-A",
  "discipline": "Piping",
  "description": "Erect Line 24-XX at Rack B",
  "area": "Rack B",
  "planned_start": "2026-09-01",
  "planned_finish": "2026-09-04",
  "actual_start": null,
  "actual_finish": null
}
```

## Match Record

``` json
{
  "event_id": "EVT-001",
  "candidate_activity_id": "PIP-101",
  "semantic_score": 0.91,
  "metadata_score": 0.95,
  "temporal_score": 0.90,
  "llm_score": 0.95,
  "final_confidence": 0.94,
  "decision": "auto_match",
  "reviewer": null,
  "reason": [
    "Same discipline",
    "Same location",
    "Same line number",
    "Same execution action",
    "Compatible schedule window"
  ]
}
```

------------------------------------------------------------------------

# 7. Ingestion Pipeline

## Input 1 --- Schedule Excel

Required columns:

-   Activity ID
-   WBS
-   Activity description
-   Discipline
-   Area/location
-   Planned Start
-   Planned Finish
-   Optional tags/line/equipment IDs

Normalize:

-   Dates
-   Case
-   Abbreviations
-   Units
-   Empty fields

Store both: - Original row - Normalized representation

## Input 2 --- DPR

Extract:

-   Date
-   Discipline
-   Activity/event description
-   Location
-   Tags/line numbers
-   Status
-   Quantity if present
-   Manpower if present

## Input 3 --- Discipline spreadsheet

Map varying column names to the canonical schema.

Examples:

``` text
"Work Description"
"Activity"
"Job Description"
"Progress Description"
```

all become:

``` text
activity_description
```

------------------------------------------------------------------------

# 8. LLM Extraction

Use structured output only.

Prompt concept:

``` text
You are a construction progress extraction system.

Extract only information explicitly present in the source.

Return:
- discipline
- activity_description
- action
- status
- location
- equipment_tag
- line_number
- event_date
- quantity
- unit
- evidence_text

Never invent an activity ID.
Never infer a completion date unless supported by the source.
```

Important: - Preserve raw evidence. - Never let the LLM directly write
to the schedule. - Validate output against the schema.

------------------------------------------------------------------------

# 9. Terminology Normalization

Create a construction terminology dictionary.

Example:

``` text
"spool erected"
"spool installed"
"spool mounting"
"erection of spool"
"line erection"
```

can map to canonical concepts such as:

``` text
PIPING / ERECTION
```

Other examples:

``` text
"cable pulling"
"pulling cable"
"cable laid"
→ ELECTRICAL / CABLE INSTALLATION

"rebar fixed"
"reinforcement completed"
"steel fixing"
→ CIVIL / REINFORCEMENT
```

Do not make this dictionary purely static.

Store reviewer corrections so it can grow over time.

------------------------------------------------------------------------

# 10. Matching Engine

This is the technical centerpiece.

## Stage 1 --- Hard filtering

Reduce candidates using:

-   Discipline
-   Area
-   WBS
-   Line number
-   Equipment tag
-   Date
-   Activity status

Example:

``` text
Piping event
↓
Ignore Civil/Electrical activities
↓
Rack B
↓
Ignore other areas
↓
Line 24-XX
↓
Candidate set becomes small
```

## Stage 2 --- Semantic retrieval

Generate embeddings for:

-   Field event
-   Schedule activity descriptions

Use vector similarity to retrieve Top-K candidates.

Recommended K: - 5 to 10

## Stage 3 --- LLM reranking

Provide only the candidate activities to the LLM.

Ask it to evaluate:

-   action
-   object
-   location
-   discipline
-   tags
-   temporal compatibility
-   granularity

## Stage 4 --- Deterministic validation

Reject/penalize impossible matches.

Examples:

-   Discipline mismatch.
-   Explicit line number mismatch.
-   Completion event for an already completed incompatible activity.
-   Event date outside reasonable context.
-   Hydrotest event mapped to erection activity.

------------------------------------------------------------------------

# 11. Confidence Model

Do not use raw LLM confidence.

Use a combined score.

Example:

``` text
Final Score =
0.35 × semantic similarity
+ 0.25 × metadata match
+ 0.20 × LLM reranking
+ 0.10 × temporal compatibility
+ 0.10 × terminology/tag match
```

Weights are prototype values and should be configurable.

## Decision thresholds

``` text
>= 0.90
AUTO-MATCH

0.70–0.89
REVIEW REQUIRED

< 0.70
UNMATCHED
```

These thresholds should be tuned using your benchmark dataset.

------------------------------------------------------------------------

# 12. Human-in-the-Loop Review

Reviewer screen:

``` text
FIELD EVENT

"Piping crew completed erection of 24-inch
spool at Rack B."

--------------------------------------------

TOP CANDIDATES

PIP-101   94%   ✓
Erect Line 24-XX at Rack B

PIP-102   63%
Weld Line 24-XX at Rack B

PIP-113   28%
Install support for Line 25-XX

--------------------------------------------

WHY PIP-101?

✓ Piping
✓ Rack B
✓ 24-inch line
✓ Erection
✓ Compatible date

[ APPROVE ] [ CORRECT ] [ UNMATCHED ]
```

This screen is critical for the demo.

------------------------------------------------------------------------

# 13. Audit Trail

Every update should store:

``` text
Event ID
Source document
Page/cell/line
Original text
Extracted data
Candidate activities
Scores
Rules applied
Final decision
Reviewer
Timestamp
Previous schedule value
New schedule value
```

Example:

``` text
PIP-101
Actual Finish
Before: null
After: 08-Sep-2026

Source: DPR-08-Sep.pdf
Evidence: Page 2
Decision: Planner Approved
AI Confidence: 0.94
```

This directly addresses trust.

------------------------------------------------------------------------

# 14. Schedule Update

For the MVP, use the uploaded schedule as the source of truth.

When approved:

``` text
actual_start
actual_finish
```

are updated in your database.

Show a downloadable updated schedule.

If real Primavera integration is not available:

-   Do not fake live P6 integration.
-   Demonstrate an integration-ready API boundary.
-   Explain that production deployment can connect through supported
    Primavera/PMIS APIs.

------------------------------------------------------------------------

# 15. Analytics Dashboard

Minimum metrics:

``` text
Total L5/L6 activities
Actualized activities
Auto-matched %
Review %
Unmatched %
Average confidence
Delayed activities
```

Example:

``` text
ACTIVITY RECONCILIATION

1,248 total
────────────────────────
89% auto-matched
 8% review
 3% unmatched

Average confidence: 91%

Schedule impact:
Delayed: 47
Completed early: 23
On time: 816
```

------------------------------------------------------------------------

# 16. Institutional Memory

For every validated activity, store:

-   Planned duration
-   Actual duration
-   Start variance
-   Finish variance
-   Discipline
-   Location
-   Contractor
-   Manpower if available
-   Delay cause if reported
-   Source evidence

Future query examples:

``` text
"What was the actual duration of similar piping erection?"

"Which areas repeatedly experienced delays?"

"Which contractors had the largest average schedule variance?"

"What activities commonly overrun their baseline duration?"
```

For the hackathon, demonstrate this with historical synthetic projects.

------------------------------------------------------------------------

# 17. Optional Voice Agent

Only add after the core pipeline works.

Demo:

Supervisor: \> "Piping team completed the 24-inch spool at Rack B
today."

System: \> "I found PIP-101, Erect Line 24-XX at Rack B, with 94%
confidence. Mark as completed?"

Supervisor: \> "Yes."

System: \> "PIP-101 updated."

Architecture:

``` text
Voice
↓
Speech-to-text
↓
Same extraction pipeline
↓
Same matching engine
```

Do not build a separate voice-specific backend.

------------------------------------------------------------------------

# 18. Data Strategy

Because live project data is unavailable, create a synthetic benchmark.

## Dataset target

At least:

-   300 schedule activities
-   150 field events
-   4 disciplines
-   3 input formats
-   30+ ambiguous cases

Include:

### Easy cases

Exact terminology.

### Synonym cases

"spool erected" vs "erect line".

### Abbreviation cases

"FAB", "ERECT", "INST", etc.

### Missing-ID cases

No explicit activity ID.

### Granularity cases

One field report covering multiple schedule activities.

### Ambiguous cases

Two similar candidate activities.

### Negative cases

Correct discipline but wrong location/activity.

------------------------------------------------------------------------

# 19. Evaluation Plan

Create ground-truth labels manually.

Measure:

## Extraction

-   Field accuracy
-   Event status accuracy
-   Date accuracy

## Matching

-   Top-1 accuracy
-   Top-3 recall
-   High-confidence precision
-   False auto-match rate

## Workflow

-   Percentage auto-matched
-   Percentage requiring review
-   Percentage unresolved

Most important:

> **High-confidence precision should be very high.**

It is better to send an ambiguous event to a human than confidently
update the wrong activity.

------------------------------------------------------------------------

# 20. Example Benchmark

Target:

``` text
150 field events

Top-1 correct match:        >= 85%
Top-3 candidate recall:    >= 95%
High-confidence precision: >= 95%
False auto-match rate:     <= 5%
Extraction accuracy:       >= 90%
```

These are internal prototype targets, not claims of production
performance.

------------------------------------------------------------------------

# 21. UI Pages

## Page 1 --- Project Dashboard

-   Project name
-   Activity count
-   Reconciliation status
-   Delays
-   Confidence

## Page 2 --- Upload Center

-   Schedule
-   DPR
-   Discipline spreadsheets

## Page 3 --- Extraction

Show extracted events and source evidence.

## Page 4 --- Matching

Show top candidates and confidence.

## Page 5 --- Review Queue

Approve/correct/unmatched.

## Page 6 --- Schedule

Show planned vs actual dates.

## Page 7 --- Analytics

Show: - progress - delays - discipline trends - actual vs planned
duration

## Page 8 --- Project Memory

Natural-language query over historical execution data.

------------------------------------------------------------------------

# 22. Suggested API Endpoints

``` text
POST /projects
POST /projects/{id}/schedule/upload
POST /projects/{id}/documents/upload

POST /projects/{id}/extract
GET  /projects/{id}/events

POST /events/{id}/match
GET  /events/{id}/candidates

POST /matches/{id}/approve
POST /matches/{id}/correct
POST /matches/{id}/reject

GET /projects/{id}/schedule
GET /projects/{id}/analytics

GET /projects/{id}/audit-log

POST /projects/{id}/memory/query
```

------------------------------------------------------------------------

# 23. Database Tables

Minimum:

``` text
projects
schedule_activities
source_documents
execution_events
activity_matches
review_decisions
audit_logs
terminology
historical_activity_stats
```

Optional:

``` text
activity_embeddings
contractors
delay_causes
```

------------------------------------------------------------------------

# 24. Development Phases

## Phase 1 --- Domain and Dataset

Deliverables:

-   Synthetic project
-   Schedule dataset
-   DPR dataset
-   Terminology dictionary
-   Ground truth

Do not start with UI.

------------------------------------------------------------------------

## Phase 2 --- Basic Ingestion

Build:

-   Excel parser
-   PDF/text parser
-   Canonical event schema
-   Schedule database

Success condition:

> All inputs become structured records.

------------------------------------------------------------------------

## Phase 3 --- AI Extraction

Build:

-   LLM extraction
-   Validation
-   Evidence preservation

Success condition:

> DPR → structured execution event.

------------------------------------------------------------------------

## Phase 4 --- Matching Engine

Build:

-   metadata filtering
-   embeddings
-   Top-K retrieval
-   LLM reranking
-   rule validation

Success condition:

> Field event → correct L5/L6 candidate.

This is the highest-priority engineering phase.

------------------------------------------------------------------------

## Phase 5 --- Confidence + Review

Build:

-   confidence scoring
-   review queue
-   approve/correct/unmatched workflow

Success condition:

> Ambiguous cases do not get silently auto-updated.

------------------------------------------------------------------------

## Phase 6 --- Schedule Update

Build:

-   actual start/end update
-   before/after comparison
-   audit record

Success condition:

> Approved event changes schedule state.

------------------------------------------------------------------------

## Phase 7 --- Dashboard

Build:

-   project summary
-   reconciliation metrics
-   schedule variance
-   discipline analytics

------------------------------------------------------------------------

## Phase 8 --- Institutional Memory

Build:

-   historical activity records
-   query interface
-   simple delay-pattern analytics

------------------------------------------------------------------------

## Phase 9 --- Voice

Only if everything above is stable.

------------------------------------------------------------------------

# 25. Hackathon Time Allocation

For a typical 24--36 hour build:

## 0--3 hours

Understand PS + finalize schema + create dataset.

## 3--7 hours

Backend + database + ingestion.

## 7--12 hours

LLM extraction + normalization.

## 12--18 hours

Matching engine.

## 18--22 hours

Confidence + review workflow.

## 22--26 hours

Dashboard + schedule update.

## 26--30 hours

Institutional memory + analytics.

## 30--34 hours

Testing + demo data + polish.

## Final hours

Pitch + judge Q&A + backup demo.

If time gets short, remove voice before removing matching/review/audit.

------------------------------------------------------------------------

# 26. Team Responsibilities

## Member 1 --- AI/ML

-   LLM extraction
-   embeddings
-   reranking
-   confidence logic

## Member 2 --- Backend

-   FastAPI
-   PostgreSQL
-   ingestion
-   APIs

## Member 3 --- Frontend

-   dashboard
-   matching screen
-   review workflow

## Member 4 --- Data/Domain

-   synthetic construction data
-   schedule structure
-   terminology
-   ground truth
-   evaluation

## Member 5 --- Integration/Analytics

-   schedule update
-   analytics
-   audit
-   deployment

## Member 6 --- Product/Pitch

-   UX
-   demo flow
-   presentation
-   documentation
-   judge Q&A

------------------------------------------------------------------------

# 27. Competitive Positioning

Do not position the product as:

> "Another construction management platform."

Position it as:

> **A semantic reconciliation layer that connects messy field execution
> data to existing structured project schedules.**

Existing platforms such as Procore, Autodesk Construction Cloud, Oracle
Aconex and Bentley SYNCHRO already address broad field reporting,
project controls and construction management.

Your differentiation:

``` text
Existing system
     ↓
Existing schedule
     ↓
Existing field reports
     ↓
YOUR INTELLIGENCE LAYER
     ↓
Trusted L5/L6 actuals
```

The customer does not necessarily need to replace existing systems.

------------------------------------------------------------------------

# 28. Research-Informed Design Principle

Use a hybrid/neuro-symbolic architecture:

``` text
LLM
+
Embeddings
+
Knowledge/terminology layer
+
Deterministic constraints
+
Human review
```

Avoid:

``` text
DPR
 ↓
LLM
 ↓
Activity ID
 ↓
Automatic schedule update
```

The second architecture is difficult to defend because a hallucinated
match can corrupt project controls.

------------------------------------------------------------------------

# 29. Judge Questions and Answers

## Q1. Why not just use an LLM?

Answer:

> The problem requires reliable entity matching, not text generation. We
> use the LLM for extraction and reasoning, while metadata, vector
> retrieval and deterministic constraints restrict the candidate space.
> Ambiguous cases go to human review.

Follow-up: \> What if the LLM is wrong?

Answer: \> It cannot directly update the schedule. The confidence and
validation layers determine whether automation is permitted.

------------------------------------------------------------------------

## Q2. How is this different from Procore/Autodesk?

Answer:

> Those are broad construction management platforms. Our focused problem
> is the translation of heterogeneous field language into existing L5/L6
> schedule structures without requiring the organization to replace its
> current planning system.

Follow-up: \> Why wouldn't they build this?

Answer: \> They could, but our prototype demonstrates a specialized
reconciliation layer that can potentially operate across multiple
existing reporting formats and schedule systems.

------------------------------------------------------------------------

## Q3. Your data is synthetic. How do you prove accuracy?

Answer:

> Live project data is confidential by design. We therefore build a
> controlled benchmark containing terminology variation, missing IDs,
> ambiguous activities, different disciplines and granularity
> mismatches. We measure extraction and matching separately and
> explicitly report unresolved cases.

------------------------------------------------------------------------

## Q4. Can you integrate with Primavera?

Answer:

> The MVP treats a schedule export as the system of record and exposes
> an integration API boundary. Production deployment can connect to
> supported Primavera/PMIS APIs. We avoid pretending that a mock
> integration is a production integration.

------------------------------------------------------------------------

## Q5. What happens when AI makes a wrong match?

Answer:

> The system is designed to fail safely. High-confidence validated
> events can be automated; medium-confidence events go to review;
> low-confidence events remain unmatched. Every decision retains its
> source evidence and audit trail.

------------------------------------------------------------------------

# 30. Likely Judge Challenge

A judge may ask:

> "Show me the top three matches instead of one."

The system should already support this.

Display:

``` text
PIP-101   94%
PIP-102   63%
PIP-113   28%
```

The reviewer selects the correct activity.

The backend then:

``` text
1. Updates schedule.
2. Stores correction.
3. Stores terminology/context.
4. Uses the decision as future feedback.
```

This can be demonstrated live.

------------------------------------------------------------------------

# 31. Biggest Technical Risk

## Semantic matching accuracy

Not:

-   UI
-   Excel parsing
-   LLM API calls
-   dashboard

The critical question is:

> **How do you know that the field statement refers to this exact L5/L6
> activity?**

Therefore spend the largest amount of engineering effort on:

-   candidate retrieval
-   metadata filtering
-   semantic matching
-   temporal validation
-   confidence
-   human review

------------------------------------------------------------------------

# 32. Biggest Product Risk

Do not over-automate.

The product should communicate:

> **"AI handles the obvious work. Humans handle the exceptions."**

This is more credible than claiming full autonomous schedule management.

------------------------------------------------------------------------

# 33. Killer Demo

Use this exact sequence:

### 1. Upload schedule

> 1,248 L5/L6 activities imported.

### 2. Upload DPR

> Piping crew completed erection of 24-inch spool at Rack B.

### 3. AI extraction

``` text
Discipline: Piping
Action: Erection
Object: 24-inch spool
Location: Rack B
Status: Completed
```

### 4. Matching

``` text
PIP-101 — 94%
PIP-102 — 63%
PIP-113 — 28%
```

### 5. Explainability

``` text
✓ Same discipline
✓ Same location
✓ Same line
✓ Same action
✓ Compatible date
```

### 6. Approve

> Actual Finish = 08-Sep-2026

### 7. Schedule variance

> Baseline Finish = 06-Sep-2026\
> Actual Finish = 08-Sep-2026\
> Variance = +2 days

### 8. Historical insight

> Similar piping activities historically exceeded planned duration by
> 1.4 days.

### 9. Final message

> **From field language to schedule-ready actuals in seconds.**

------------------------------------------------------------------------

# 34. What to Say in the Pitch

## Opening

> "A construction schedule knows exactly what should happen. The field
> knows exactly what did happen. The problem is that they speak
> different languages."

Then:

> "A planner may have 'Erect Line 24-XX at Rack B' in Primavera. A
> supervisor may simply report '24-inch spool erected at Rack B.' Today,
> someone has to manually reconcile those two statements."

Then introduce:

> "Our system acts as the intelligence layer between them."

------------------------------------------------------------------------

# 35. Final Product Definition

## Product Name

Use a temporary working name such as:

**Field2Schedule AI**

## Tagline

> **From field language to schedule intelligence.**

## Core modules

``` text
1. Multi-format ingestion
2. AI event extraction
3. Terminology normalization
4. Semantic activity matching
5. Confidence engine
6. Human review
7. Schedule actualization
8. Audit trail
9. Performance analytics
10. Institutional memory
```

------------------------------------------------------------------------

# 36. Final Priority Matrix

  Feature                   Priority Build?
  ----------------------- ---------- -------------------
  Schedule ingestion              P0 YES
  DPR ingestion                   P0 YES
  Structured extraction           P0 YES
  Semantic matching               P0 YES
  Confidence scoring              P0 YES
  Review queue                    P0 YES
  Schedule update                 P0 YES
  Audit trail                     P0 YES
  Dashboard                       P1 YES
  Historical memory               P1 YES
  Voice interface                 P2 Only if time
  OCR                             P2 Optional
  Real P6 integration             P2 Mock/API boundary
  Forecasting                     P3 Optional
  Computer vision                 P3 NO
  Blockchain                      P3 NO
  AR/VR                           P3 NO

------------------------------------------------------------------------

# 37. Definition of Done

The MVP is successful when a judge can perform this sequence:

``` text
Upload schedule
       ↓
Upload field report
       ↓
See extracted execution event
       ↓
See top L5/L6 candidates
       ↓
Understand why one candidate won
       ↓
Approve/correct it
       ↓
See actual date update
       ↓
See schedule variance
       ↓
See the event stored as historical knowledge
```

If this entire loop works reliably, the prototype has solved the central
PS.

------------------------------------------------------------------------

# 38. Final Strategy

## Build the boring core extremely well.

The winning system is not:

> 15 AI features + voice + chatbot + AR + blockchain.

It is:

> **Messy field report → accurate structured event → correct L5/L6 match
> → safe schedule update → auditable historical record.**

Everything else should support that loop.

## Final architecture principle

> **LLM for language.\
> Embeddings for retrieval.\
> Rules for constraints.\
> Humans for ambiguity.\
> Database for truth.**

That should be the technical philosophy of the entire project.

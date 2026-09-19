# SetuAI — Design

Source of truth: `plan.md` §12, §15, §21. This document restates it; it does not re-derive it.

## UI Principle

The UI should prioritize the demo flow and communicate value within seconds:

```text
Upload Schedule → Submit Field Update → AI Processes Update →
AI Suggests Activity → Review Match → Approve → Progress Dashboard Updates
```

Avoid building dozens of screens. Prefer: a clean dashboard, clear status indicators, obvious
actions, readable tables, confidence visualization, visible AI reasoning, and a before/after
progress view.

## Pages

1. **Project Dashboard** — project name, activity count, reconciliation status, delays, confidence.
2. **Upload Center** — schedule, DPR, discipline spreadsheets.
3. **Extraction** — extracted events with source evidence shown alongside.
4. **Matching** — top candidates with confidence.
5. **Review Queue** — approve / correct / unmatched actions.
6. **Schedule** — planned vs actual dates.
7. **Analytics** — progress, delays, discipline trends, actual vs planned duration.
8. **Project Memory** — natural-language query over historical execution data.

## The Reviewer Screen (critical for the demo)

```text
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

Always show top-3 candidates, not just the winner — judges are expected to ask for this
(`plan.md` §30). Explainability (the ✓ checklist) is the single strongest trust signal in the
product and should never be simplified away to just a percentage.

## Confidence Visualization

Show the composite score plus its component breakdown (semantic / metadata / LLM-rerank /
temporal / terminology), not just the final number — this is what makes "matched because ✓✓✓"
possible. See `context.md` §10 for the formula and `docs/API.md` for how components are returned.

## Analytics Dashboard — Minimum Metrics

```text
Total L5/L6 activities
Actualized activities
Auto-matched %
Review %
Unmatched %
Average confidence
Delayed activities
```

Example target presentation:

```text
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

## Human-in-the-Loop Design Rule

No uncertain AI prediction may silently modify project data. Thresholds (configurable, not
scientifically validated — say so if asked):

```text
>= 90%     Suggested Match (auto-match)
70–89%     Human Review Required
< 70%      Uncertain / Unmatched
```

The final decision always belongs to the user. This is the product's core credibility claim:
"AI handles the obvious work. Humans handle the exceptions."

## Voice Interface (optional, deferred)

Only build after the core pipeline is stable. If built, route through the exact same extraction and
matching pipeline — do not build a separate voice-specific backend.

```text
Supervisor: "Piping team completed the 24-inch spool at Rack B today."
System: "I found PIP-101, Erect Line 24-XX at Rack B, with 94% confidence. Mark as completed?"
Supervisor: "Yes."
System: "PIP-101 updated."
```

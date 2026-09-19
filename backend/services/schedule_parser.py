"""
SetuAI — Schedule Parser (Slice 1)

Parses an uploaded schedule file (.xlsx/.xls/.csv) into validated
`schemas.ScheduleActivity` records. Field-report/DPR parsing (Slice 2/3) is a
separate module — this file only handles the baseline schedule.

Column names vary by source (plan.md notes terminology drift even at the
schedule level), so headers are matched case-insensitively against a small
synonym list per canonical field rather than requiring an exact header name.

Never raises on a bad row — bad rows are skipped and reported as warnings so
one malformed row doesn't block the rest of an import (plan.md §25, error
handling: give the user understandable errors, don't hide failures).
"""

import io
from datetime import date

import pandas as pd

from models.schemas import Discipline, ScheduleActivity

# Canonical field -> accepted header synonyms (matched case-insensitively, trimmed).
COLUMN_SYNONYMS: dict[str, list[str]] = {
    "activity_id": ["activity id", "id", "task id", "wbs id"],
    "wbs": ["wbs", "wbs code"],
    "discipline": ["discipline", "trade"],
    "description": [
        "activity",
        "description",
        "work description",
        "job description",
        "task description",
        "activity description",
    ],
    "area": ["location", "area", "zone", "rack"],
    "planned_start": ["planned start", "start date", "planned start date"],
    "planned_finish": [
        "planned finish",
        "finish date",
        "planned finish date",
        "planned end",
    ],
}

REQUIRED_FIELDS = ["activity_id", "discipline", "description", "planned_start", "planned_finish"]

# Discipline text variants -> canonical enum value.
DISCIPLINE_SYNONYMS: dict[str, Discipline] = {
    "civil": Discipline.CIVIL,
    "piping": Discipline.PIPING,
    "pipe": Discipline.PIPING,
    "electrical": Discipline.ELECTRICAL,
    "elec": Discipline.ELECTRICAL,
    "instrumentation": Discipline.INSTRUMENTATION,
    "instrument": Discipline.INSTRUMENTATION,
    "inst": Discipline.INSTRUMENTATION,
}


def _build_header_map(columns: list[str]) -> dict[str, str]:
    """Returns {canonical_field: actual_column_name} for whatever headers are present."""
    normalized = {str(c).strip().lower(): c for c in columns}
    header_map: dict[str, str] = {}
    for field, synonyms in COLUMN_SYNONYMS.items():
        for synonym in synonyms:
            if synonym in normalized:
                header_map[field] = normalized[synonym]
                break
    return header_map


def _parse_date(value) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        parsed = pd.to_datetime(value)
        return parsed.date()
    except (ValueError, TypeError):
        return None


def _parse_discipline(value: str) -> Discipline | None:
    key = str(value).strip().lower()
    return DISCIPLINE_SYNONYMS.get(key)


def parse_schedule_file(
    filename: str, content: bytes
) -> tuple[list[ScheduleActivity], list[str]]:
    """
    Parses schedule file bytes into (activities, warnings).
    Supports .xlsx/.xls (openpyxl) and .csv.
    """
    lower_name = filename.lower()
    if lower_name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    elif lower_name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(content))
    else:
        return [], [f"Unsupported file type: {filename}. Use .xlsx, .xls, or .csv."]

    header_map = _build_header_map(list(df.columns))
    missing_required = [f for f in REQUIRED_FIELDS if f not in header_map]
    if missing_required:
        return [], [
            "Missing required column(s): "
            + ", ".join(missing_required)
            + ". Recognized headers: "
            + ", ".join(sorted({s for f in REQUIRED_FIELDS for s in COLUMN_SYNONYMS[f]}))
        ]

    activities: list[ScheduleActivity] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()

    for idx, row in df.iterrows():
        row_num = idx + 2  # +1 for 0-index, +1 for header row

        activity_id = str(row.get(header_map["activity_id"], "")).strip()
        if not activity_id or activity_id.lower() == "nan":
            warnings.append(f"Row {row_num}: skipped — missing Activity ID.")
            continue
        if activity_id in seen_ids:
            warnings.append(f"Row {row_num}: skipped — duplicate Activity ID '{activity_id}'.")
            continue

        discipline = _parse_discipline(row.get(header_map["discipline"], ""))
        if discipline is None:
            warnings.append(
                f"Row {row_num} ('{activity_id}'): skipped — unrecognized discipline "
                f"'{row.get(header_map['discipline'], '')}'."
            )
            continue

        description = str(row.get(header_map["description"], "")).strip()
        if not description or description.lower() == "nan":
            warnings.append(f"Row {row_num} ('{activity_id}'): skipped — missing description.")
            continue

        planned_start = _parse_date(row.get(header_map["planned_start"]))
        planned_finish = _parse_date(row.get(header_map["planned_finish"]))
        if planned_start is None or planned_finish is None:
            warnings.append(
                f"Row {row_num} ('{activity_id}'): skipped — invalid or missing planned dates."
            )
            continue

        wbs = str(row.get(header_map.get("wbs", ""), "")).strip() if "wbs" in header_map else ""
        if wbs.lower() == "nan":
            wbs = ""
        area = str(row.get(header_map.get("area", ""), "")).strip() if "area" in header_map else ""
        if area.lower() == "nan":
            area = ""
        if not wbs:
            warnings.append(f"Row {row_num} ('{activity_id}'): no WBS column — stored blank.")
        if not area:
            warnings.append(f"Row {row_num} ('{activity_id}'): no Area/Location column — stored blank.")

        activities.append(
            ScheduleActivity(
                activity_id=activity_id,
                wbs=wbs,
                discipline=discipline,
                description=description,
                area=area,
                planned_start=planned_start,
                planned_finish=planned_finish,
                actual_start=None,
                actual_finish=None,
            )
        )
        seen_ids.add(activity_id)

    return activities, warnings

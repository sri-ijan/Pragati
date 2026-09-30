"""Requirement 5: the extracted event can be persisted and retrieved."""

from datetime import date

from models.schemas import Discipline, EventStatus, ExecutionEvent
from repositories.execution_event_repository import (
    get_events_for_project,
    save_execution_event,
)


def _sample_event() -> ExecutionEvent:
    return ExecutionEvent(
        event_id="EVT-test-1",
        source_id="doc-123",
        discipline=Discipline.ELECTRICAL,
        activity_description="Cable tray installation",
        action="installation",
        status=EventStatus.IN_PROGRESS,
        location="Rack B",
        equipment_tag=None,
        line_number=None,
        event_date=date(2026, 9, 20),
        quantity=60,
        unit="%",
        raw_text="Rack B mein cable tray ka kaam mostly complete ho gaya hai, around 60% done.",
        confidence=None,
    )


def test_execution_event_persists_and_is_retrievable(db_session):
    event = _sample_event()

    save_execution_event(db_session, project_id="proj-123", event=event)
    rows = get_events_for_project(db_session, project_id="proj-123")

    assert len(rows) == 1
    stored = rows[0]
    assert stored.event_id == "EVT-test-1"
    assert stored.discipline == "Electrical"
    assert stored.status == "in_progress"
    assert stored.quantity == 60
    assert stored.raw_text == event.raw_text


def test_events_scoped_to_project_and_status_filter_works(db_session):
    save_execution_event(db_session, project_id="proj-A", event=_sample_event())

    other = _sample_event()
    other.event_id = "EVT-test-2"
    other.status = EventStatus.COMPLETED
    save_execution_event(db_session, project_id="proj-B", event=other)

    proj_a_events = get_events_for_project(db_session, project_id="proj-A")
    assert len(proj_a_events) == 1
    assert proj_a_events[0].event_id == "EVT-test-1"

    proj_b_completed = get_events_for_project(db_session, project_id="proj-B", status="completed")
    assert len(proj_b_completed) == 1
    proj_b_in_progress = get_events_for_project(db_session, project_id="proj-B", status="in_progress")
    assert len(proj_b_in_progress) == 0
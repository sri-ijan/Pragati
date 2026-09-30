"""
Requirement 7: existing Slice 1/2 functionality still builds and works.
This doesn't re-run the full manual browser verification already done for
Slices 1-2 — it's a fast regression check that main.py still imports cleanly
with every router wired (schedule/documents/projects/health unchanged) and
that the basic health check still responds, run against a throwaway SQLite
DB rather than requiring Postgres for a CI-style test run.
"""

from fastapi.testclient import TestClient


def test_app_imports_and_wires_all_routers_including_new_extraction_router():
    import main  # importing alone proves every router module wires cleanly

    route_paths = {route.path for route in main.app.routes}
    # Slice 1/2 endpoints, unchanged:
    assert "/health" in route_paths
    assert "/projects" in route_paths
    assert "/projects/{project_id}/schedule/upload" in route_paths
    assert "/projects/{project_id}/schedule" in route_paths
    assert "/projects/{project_id}/documents/upload" in route_paths
    assert "/projects/{project_id}/documents" in route_paths
    # Slice 3 additions:
    assert "/projects/{project_id}/extract" in route_paths
    assert "/projects/{project_id}/events" in route_paths
    # Slice 4 additions:
    assert "/events/{event_id}/match" in route_paths
    assert "/events/{event_id}/candidates" in route_paths


def test_health_endpoint_still_responds():
    import main

    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
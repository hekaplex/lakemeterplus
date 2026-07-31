"""Behavioral tests for ObservabilityAllowlistMiddleware
(app/observability/core/allowlist.py) — docs/merge-tasks.md task #8.

This middleware is deliberately scoped to /api/v1/observability/* only, so
it doesn't change access control for Lakemeter's own routes. These tests
exist specifically to pin that scoping — a regression here (e.g. someone
"simplifying" the path check) would silently change authz for the whole
merged app.
"""


def test_lakemeter_route_is_unaffected_by_observability_allowlist(client):
    # No identity header at all — if the allowlist were accidentally
    # applied app-wide, this would 403. It must not.
    response = client.get("/health")
    assert response.status_code == 200


def test_observability_health_is_public(client):
    response = client.get("/api/v1/observability/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_observability_route_requires_identity(client):
    response = client.get("/api/v1/observability/cost/summary")
    assert response.status_code == 403


def test_observability_route_passes_gate_with_identity(client, user_headers):
    response = client.get("/api/v1/observability/cost/summary", headers=user_headers)
    # The allowlist gate must let this through (not 403) — what happens
    # next depends on real Databricks/SQL Warehouse connectivity, which
    # this test environment doesn't have, so we only assert the gate
    # didn't block it.
    assert response.status_code != 403


def test_allowlist_enforced_when_configured(client, monkeypatch):
    from app.config import settings

    # monkeypatch restores the original value automatically after the test.
    monkeypatch.setattr(settings, "allowed_users", "bob@example.com")

    response = client.get(
        "/api/v1/observability/cost/summary",
        headers={"X-Forwarded-User": "alice@example.com"},
    )
    assert response.status_code == 403

    response = client.get(
        "/api/v1/observability/cost/summary",
        headers={"X-Forwarded-User": "bob@example.com"},
    )
    assert response.status_code != 403

"""Regression test for a bug introduced (and fixed) while migrating
UserPermissionsService off Delta tables onto Lakebase (docs/merge-tasks.md
task #16): admin.py's routes originally called require_admin() as the
first line of the function body, so a non-admin was rejected with 403
before any database access happened. Adding `db: Session = Depends(get_db)`
as a route parameter meant FastAPI resolved that dependency — and could
503 if the database was unreachable — before the function body (and its
require_admin() call) ever ran, so a non-admin could get a 503 instead of
a 403 when the database happened to be down, leaking DB-health information
to an unauthorized caller ahead of the authz check.

Fixed by making require_admin itself a Depends() parameter, declared
before db: Session = Depends(get_db) — FastAPI resolves same-level
Depends() in declaration order, so the admin check now always runs first
regardless of database state. This test pins that ordering: it doesn't
matter that the test environment has no real Lakebase (Depends(get_db)
would 503), a non-admin must still see 403.
"""


def test_admin_check_wins_over_db_unavailable_for_list_users(client):
    response = client.get(
        "/api/v1/observability/admin/users",
        headers={"X-Forwarded-User": "not-an-admin@example.com"},
    )
    assert response.status_code == 403


def test_admin_check_wins_over_db_unavailable_for_upsert_user(client):
    response = client.put(
        "/api/v1/observability/admin/users",
        headers={"X-Forwarded-User": "not-an-admin@example.com"},
        json={"email": "target@example.com", "tabs": ["cost"]},
    )
    assert response.status_code == 403


def test_admin_check_wins_over_db_unavailable_for_delete_user(client):
    response = client.delete(
        "/api/v1/observability/admin/users/target@example.com",
        headers={"X-Forwarded-User": "not-an-admin@example.com"},
    )
    assert response.status_code == 403


def test_no_identity_at_all_is_still_403_not_503(client):
    # The allowlist gate (task #8) should reject this before it even
    # reaches the admin check or the DB dependency.
    response = client.get("/api/v1/observability/admin/users")
    assert response.status_code == 403

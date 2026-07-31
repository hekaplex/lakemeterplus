"""Unit tests for CostService._where() (app/observability/services/cost_service.py)
— the WHERE-clause builder used by every cost-dashboard query. This is
both the module's IDOR (cross-workspace access) protection and part of
its SQL-injection defense (values are interpolated via f-strings after
going through core/validators.py), and had zero test coverage in either
source repo. cost_service.py is the largest, most logic-heavy file in the
observability module (1,340 lines) — this covers its most security-load-
bearing piece, not the full surface area; see docs/TODO.md for what's
still untested.
"""
import pytest

from app.observability.services.cost_service import CostService


class _FakeWorkspaceClient:
    """Stands in for databricks.sdk.WorkspaceClient — CostService.__init__
    only calls get_workspace_id() on it before any SQL is touched."""

    def get_workspace_id(self):
        return "ws-current"


@pytest.fixture
def service(monkeypatch):
    from app.config import settings
    # Default: no explicit allowlist configured -> CostService scopes to
    # the current workspace only (the safe default).
    monkeypatch.setattr(settings, "allowed_workspace_ids", "")
    return CostService(client=_FakeWorkspaceClient())


class TestWhereDateRange:
    def test_includes_validated_date_bounds(self, service):
        where = service._where("2026-01-01", "2026-01-31")
        assert "u.usage_date >= '2026-01-01'" in where
        assert "u.usage_date <= '2026-01-31'" in where

    def test_rejects_malformed_date(self, service):
        with pytest.raises(ValueError):
            service._where("not-a-date", "2026-01-31")

    def test_custom_alias_is_applied(self, service):
        where = service._where("2026-01-01", "2026-01-31", alias="x")
        assert "x.usage_date >= '2026-01-01'" in where

    def test_empty_alias_omits_prefix(self, service):
        where = service._where("2026-01-01", "2026-01-31", alias="")
        assert "usage_date >= '2026-01-01'" in where
        assert ".usage_date" not in where


class TestWhereWorkspaceScoping:
    def test_defaults_to_current_workspace_only(self, service):
        # No explicit workspace_id requested -> scoped to the allowed set
        # (current workspace), not left unrestricted.
        where = service._where("2026-01-01", "2026-01-31")
        assert "workspace_id IN ('ws-current')" in where

    def test_explicit_workspace_within_allowed_set_succeeds(self, service):
        where = service._where("2026-01-01", "2026-01-31", workspace_id="ws-current")
        assert "workspace_id = 'ws-current'" in where

    def test_explicit_workspace_outside_allowed_set_is_rejected(self, service):
        # IDOR protection: a workspace the caller isn't scoped to must be
        # rejected, not silently queried.
        with pytest.raises(ValueError, match="Access denied"):
            service._where("2026-01-01", "2026-01-31", workspace_id="ws-someone-elses")

    def test_multiple_workspaces_build_in_clause(self, service, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "allowed_workspace_ids", "*")
        svc = CostService(client=_FakeWorkspaceClient())
        where = svc._where("2026-01-01", "2026-01-31", workspace_id="ws-a, ws-b")
        assert "workspace_id IN ('ws-a', 'ws-b')" in where

    def test_admin_mode_defaults_to_no_workspace_filter(self, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "allowed_workspace_ids", "*")
        svc = CostService(client=_FakeWorkspaceClient())
        where = svc._where("2026-01-01", "2026-01-31")
        assert "workspace_id" not in where

    def test_rejects_workspace_id_injection_attempt(self, service):
        with pytest.raises(ValueError):
            service._where("2026-01-01", "2026-01-31", workspace_id="ws1'; DROP TABLE usage;--")


class TestWhereTagFilter:
    def test_tag_key_only_checks_not_null(self, service):
        where = service._where("2026-01-01", "2026-01-31", tag_key="env")
        assert "custom_tags['env'] IS NOT NULL" in where

    def test_tag_value_is_escaped_not_rejected(self, service):
        where = service._where("2026-01-01", "2026-01-31", tag_key="team", tag_value="O'Brien")
        assert "custom_tags['team'] = 'O''Brien'" in where

    def test_rejects_invalid_tag_key(self, service):
        with pytest.raises(ValueError):
            service._where("2026-01-01", "2026-01-31", tag_key="bad key; DROP TABLE x;--")

"""Unit tests for the MOCK_MODE table-rewrite logic in
app/observability/core/sql_executor.py — the mechanism that lets the
observability module run demo-able on any workspace tier by swapping
`system.*` references for `workspace.mock_system_*` at query time. Zero
prior test coverage (the source repo's only test is a black-box HTTP
smoke test). `_MOCK_MODE` is read once from the environment at module
import time, so these tests monkeypatch the module-level flag directly
rather than the env var (which wouldn't be re-read after import).
"""
from app.observability.core import sql_executor


def test_rewrite_is_a_noop_when_mock_mode_disabled(monkeypatch):
    monkeypatch.setattr(sql_executor, "_MOCK_MODE", False)
    sql = "SELECT * FROM system.billing.usage WHERE workspace_id = '123'"
    assert sql_executor._rewrite_sql(sql) == sql


def test_rewrite_replaces_known_system_schemas_when_enabled(monkeypatch):
    monkeypatch.setattr(sql_executor, "_MOCK_MODE", True)
    sql = "SELECT * FROM system.billing.usage u JOIN system.billing.list_prices p ON u.sku_name = p.sku_name"
    rewritten = sql_executor._rewrite_sql(sql)
    assert "system.billing" not in rewritten
    assert rewritten.count("workspace.mock_system_billing") == 2


def test_rewrite_covers_every_schema_in_the_map(monkeypatch):
    monkeypatch.setattr(sql_executor, "_MOCK_MODE", True)
    for pattern, replacement in sql_executor._MOCK_TABLE_MAP.items():
        # Derive "system.<name>" from the replacement (not the regex pattern
        # string itself, which would need fragile parsing) — every
        # replacement follows "workspace.mock_system_<name>".
        assert replacement.startswith("workspace.mock_system_")
        name = replacement.removeprefix("workspace.mock_system_")
        schema = f"system.{name}"
        sql = f"SELECT * FROM {schema}.some_table"
        rewritten = sql_executor._rewrite_sql(sql)
        assert replacement in rewritten, f"{schema} was not rewritten to {replacement}"
        assert schema not in rewritten


def test_rewrite_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(sql_executor, "_MOCK_MODE", True)
    sql = "SELECT * FROM SYSTEM.BILLING.usage"
    rewritten = sql_executor._rewrite_sql(sql)
    assert "workspace.mock_system_billing" in rewritten.lower()


def test_rewrite_does_not_touch_unrelated_identifiers(monkeypatch):
    monkeypatch.setattr(sql_executor, "_MOCK_MODE", True)
    # "system_events" should not be mistaken for the "system" catalog thanks
    # to the \b word boundary in each pattern.
    sql = "SELECT * FROM my_catalog.system_events.log"
    assert sql_executor._rewrite_sql(sql) == sql

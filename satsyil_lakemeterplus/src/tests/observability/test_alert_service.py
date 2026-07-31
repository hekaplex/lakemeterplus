"""Unit tests for AlertService.detect_spikes() spike-detection math
(app/observability/services/alert_service.py). This logic previously had
zero test coverage in either source repo (cost-observability's own test
suite is a single black-box HTTP smoke test with no unit tests at all —
see docs/architecture-databricks-cost-observability.md).

SQL fetches are monkeypatched so these tests exercise only the pure
Python math (baseline/recent averages, spike thresholds, SKU
growth/new-SKU detection), not a real Databricks connection.
"""
import pytest

from app.observability.services.alert_service import AlertService


@pytest.fixture
def service(monkeypatch):
    # AlertService.__init__ reads get_settings().databricks_warehouse_id
    # and stores the WorkspaceClient — neither is used once we monkeypatch
    # the _fetch_* methods below, so a bare object() stands in fine.
    svc = AlertService(client=object())
    return svc


def _flat_costs(days: int, daily_cost: float) -> list[dict]:
    return [
        {"date": f"2026-06-{i + 1:02d}", "daily_cost": daily_cost, "daily_dbus": 10, "active_workspaces": 1}
        for i in range(days)
    ]


def test_no_data_returns_empty_result(service, monkeypatch):
    monkeypatch.setattr(service, "_fetch_daily_spend", lambda: [])
    monkeypatch.setattr(service, "_fetch_sku_week_over_week", lambda: [])

    result = service.detect_spikes(threshold_pct=20.0)

    assert result["has_alerts"] is False
    assert result["alert_count"] == 0
    assert result["alerts"] == []


def test_flat_spend_produces_no_spike_alert(service, monkeypatch):
    # 37 days at a constant $100/day: recent 7-day avg == baseline avg, 0% change.
    monkeypatch.setattr(service, "_fetch_daily_spend", lambda: _flat_costs(37, 100.0))
    monkeypatch.setattr(service, "_fetch_sku_week_over_week", lambda: [])

    result = service.detect_spikes(threshold_pct=20.0)

    assert result["has_alerts"] is False
    assert result["summary"]["baseline_avg_daily"] == pytest.approx(100.0)
    assert result["summary"]["recent_avg_daily"] == pytest.approx(100.0)


def test_recent_spike_above_threshold_is_detected(service, monkeypatch):
    # 30 days at $100/day baseline, then 7 days at $200/day (100% above baseline).
    rows = _flat_costs(30, 100.0) + _flat_costs(7, 200.0)
    monkeypatch.setattr(service, "_fetch_daily_spend", lambda: rows)
    monkeypatch.setattr(service, "_fetch_sku_week_over_week", lambda: [])

    result = service.detect_spikes(threshold_pct=20.0)

    assert result["has_alerts"] is True
    spike_alerts = [a for a in result["alerts"] if a["type"] == "SPEND_SPIKE"]
    assert len(spike_alerts) == 1
    assert spike_alerts[0]["severity"] == "HIGH"  # 100% > 2x the 20% threshold
    assert spike_alerts[0]["pct_change"] == pytest.approx(100.0)


def test_single_day_extreme_is_flagged_independently_of_trend(service, monkeypatch):
    # Baseline flat at $100/day for 30 days, then 6 normal days + 1 extreme
    # $500 day. The 7-day avg only moves modestly, but the single day should
    # still trip DAILY_SPIKE (>2x baseline).
    rows = _flat_costs(30, 100.0) + _flat_costs(6, 100.0) + [
        {"date": "2026-07-07", "daily_cost": 500.0, "daily_dbus": 10, "active_workspaces": 1}
    ]
    monkeypatch.setattr(service, "_fetch_daily_spend", lambda: rows)
    monkeypatch.setattr(service, "_fetch_sku_week_over_week", lambda: [])

    result = service.detect_spikes(threshold_pct=20.0)

    daily_alerts = [a for a in result["alerts"] if a["type"] == "DAILY_SPIKE"]
    assert len(daily_alerts) == 1
    assert daily_alerts[0]["cost"] == pytest.approx(500.0)


def test_new_sku_over_threshold_is_flagged(service, monkeypatch):
    monkeypatch.setattr(service, "_fetch_daily_spend", lambda: _flat_costs(37, 100.0))
    monkeypatch.setattr(service, "_fetch_sku_week_over_week", lambda: [
        {"sku_name": "BRAND_NEW_SKU", "billing_origin_product": "X", "cost_7d": "50.0", "cost_prior_7d": "0"},
    ])

    result = service.detect_spikes(threshold_pct=20.0)

    new_sku_alerts = [a for a in result["alerts"] if a["type"] == "NEW_SKU"]
    assert len(new_sku_alerts) == 1
    assert new_sku_alerts[0]["sku_name"] == "BRAND_NEW_SKU"


def test_new_sku_under_ten_dollars_is_not_flagged(service, monkeypatch):
    monkeypatch.setattr(service, "_fetch_daily_spend", lambda: _flat_costs(37, 100.0))
    monkeypatch.setattr(service, "_fetch_sku_week_over_week", lambda: [
        {"sku_name": "TINY_NEW_SKU", "billing_origin_product": "X", "cost_7d": "5.0", "cost_prior_7d": "0"},
    ])

    result = service.detect_spikes(threshold_pct=20.0)

    assert not any(a["type"] == "NEW_SKU" for a in result["alerts"])


def test_fast_growing_sku_is_flagged(service, monkeypatch):
    # threshold_pct=20 -> SKU_GROWTH trips above 1.5x threshold = 30% growth.
    monkeypatch.setattr(service, "_fetch_daily_spend", lambda: _flat_costs(37, 100.0))
    monkeypatch.setattr(service, "_fetch_sku_week_over_week", lambda: [
        {"sku_name": "GROWING_SKU", "billing_origin_product": "X", "cost_7d": "150.0", "cost_prior_7d": "100.0"},
    ])

    result = service.detect_spikes(threshold_pct=20.0)

    growth_alerts = [a for a in result["alerts"] if a["type"] == "SKU_GROWTH"]
    assert len(growth_alerts) == 1
    assert growth_alerts[0]["pct_change"] == pytest.approx(50.0)


def test_result_is_cached_within_ttl(service, monkeypatch):
    calls = {"count": 0}

    def fetch():
        calls["count"] += 1
        return _flat_costs(37, 100.0)

    monkeypatch.setattr(service, "_fetch_daily_spend", fetch)
    monkeypatch.setattr(service, "_fetch_sku_week_over_week", lambda: [])

    first = service.detect_spikes(threshold_pct=20.0)
    second = service.detect_spikes(threshold_pct=20.0)

    assert calls["count"] == 1  # second call served from cache
    assert first["alerts"] == second["alerts"]
    assert "cache_age_minutes" in second

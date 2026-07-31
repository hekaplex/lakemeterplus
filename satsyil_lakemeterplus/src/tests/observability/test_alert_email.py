"""Unit tests for app/observability/services/alert_email.py — the module
extracted in docs/merge-tasks.md task #15 so the FastAPI route and the
standalone scheduled-job script share one email implementation instead of
two. No network access — read_smtp_config_from_env/build_email_html/
build_test_email_html are all pure functions over env vars / dicts.
"""
import pytest

from app.observability.services import alert_email


def test_read_smtp_config_requires_user_password_and_recipients(monkeypatch):
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("ALERT_EMAIL_TO", raising=False)

    with pytest.raises(alert_email.SmtpConfigError, match="Missing env vars"):
        alert_email.read_smtp_config_from_env()


def test_read_smtp_config_rejects_disallowed_port(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "me@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("ALERT_EMAIL_TO", "you@example.com")
    monkeypatch.setenv("SMTP_PORT", "9999")

    with pytest.raises(alert_email.SmtpConfigError, match="SMTP_PORT"):
        alert_email.read_smtp_config_from_env()


def test_read_smtp_config_rejects_invalid_host(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "me@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("ALERT_EMAIL_TO", "you@example.com")
    monkeypatch.setenv("SMTP_HOST", "not a domain")

    with pytest.raises(alert_email.SmtpConfigError, match="SMTP_HOST"):
        alert_email.read_smtp_config_from_env()


def test_read_smtp_config_rejects_invalid_recipient(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "me@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("ALERT_EMAIL_TO", "not-an-email")

    with pytest.raises(alert_email.SmtpConfigError, match="Invalid recipient"):
        alert_email.read_smtp_config_from_env()


def test_read_smtp_config_happy_path(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "me@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("ALERT_EMAIL_TO", "you@example.com, them@example.com")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)

    host, port, user, password, recipients = alert_email.read_smtp_config_from_env()
    assert host == "smtp.gmail.com"
    assert port == 587
    assert user == "me@example.com"
    assert password == "secret"
    assert recipients == ["you@example.com", "them@example.com"]


def test_build_email_html_renders_alerts_and_escapes_content():
    result = {
        "generated_at": "2026-07-31T00:00:00Z",
        "alert_count": 1,
        "alerts": [
            {
                "type": "SPEND_SPIKE",
                "severity": "HIGH",
                "title": "<script>alert(1)</script>",
                "detail": "spend up 42%",
            }
        ],
        "summary": {
            "total_30d": 1234.56,
            "recent_avg_daily": 78.9,
            "pct_vs_baseline": 42.0,
        },
    }

    html = alert_email.build_email_html(result, threshold_pct=20.0, app_url="https://example.com")

    assert "<script>alert(1)</script>" not in html  # must be HTML-escaped
    assert "&lt;script&gt;" in html
    assert "HIGH" in html
    assert "1,234.56" in html
    assert "https://example.com" in html


def test_build_email_html_handles_no_alerts():
    result = {"generated_at": "", "alert_count": 0, "alerts": [], "summary": {}}
    html = alert_email.build_email_html(result, threshold_pct=20.0, app_url="")
    assert "<html>" in html


def test_build_test_email_html_is_static_and_safe():
    html = alert_email.build_test_email_html()
    assert "Test Alert" in html

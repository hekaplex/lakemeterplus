"""Cost spike alert endpoints — summary, test email, config check.

Email building/sending is shared with the standalone scheduled-job script
(app/observability/scripts/send_cost_alerts.py) via services/alert_email.py
— see satsyil_lakemeterplus/docs/merge-tasks.md task #15.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.observability.core.dependencies import get_workspace_client, require_admin
from app.observability.core.validators import validate_threshold_pct
from app.observability.services import alert_email

router = APIRouter(prefix="/alerts", tags=["Alerts"])
_log = logging.getLogger(__name__)


def _svc(request: Request):
    from app.observability.services.alert_service import AlertService
    return AlertService(get_workspace_client())


def _smtp_config_or_400():
    try:
        return alert_email.read_smtp_config_from_env()
    except alert_email.SmtpConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _send_or_500(*args, **kwargs):
    try:
        alert_email.send_email(*args, **kwargs)
    except alert_email.EmailSendError as exc:
        _log.error("EMAIL_SEND_FAILED error=%s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Read endpoints (any authenticated user) ──────────────────────────────────

@router.get("/summary")
def get_alert_summary(
    threshold_pct: float = Query(default=20.0, ge=1.0, le=100.0),
    svc=Depends(_svc),
):
    """Return current spike detection results."""
    try:
        pct = validate_threshold_pct(threshold_pct)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return svc.detect_spikes(threshold_pct=pct)


# ── Admin-only endpoints ──────────────────────────────────────────────────────

@router.get("/config")
def get_alert_config(request: Request):
    """Return which alert env vars are configured (admin only, values masked)."""
    require_admin(request)
    keys = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
            "ALERT_EMAIL_TO", "ALERT_THRESHOLD_PCT", "APP_URL"]
    return {
        k: ("✓ set" if os.environ.get(k) else "✗ not set")
        for k in keys
    }


@router.post("/test-email")
def send_test_email(request: Request):
    """Send a test alert email to verify SMTP config (admin only)."""
    require_admin(request)
    smtp_host, smtp_port, smtp_user, smtp_pass, recipients = _smtp_config_or_400()
    _send_or_500(smtp_host, smtp_port, smtp_user, smtp_pass, recipients,
                 "Test Alert — Databricks Cost Observability", alert_email.build_test_email_html())
    return {"status": "sent", "to": recipients[0]}


@router.post("/send-now")
def send_alerts_now(
    request: Request,
    threshold_pct: float = Query(default=20.0, ge=1.0, le=100.0),
    svc=Depends(_svc),
):
    """Trigger an immediate alert email (admin only — only sends if alerts exist)."""
    require_admin(request)
    try:
        pct = validate_threshold_pct(threshold_pct)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    smtp_host, smtp_port, smtp_user, smtp_pass, recipients = _smtp_config_or_400()
    app_url = os.environ.get("APP_URL", "")

    result = svc.detect_spikes(threshold_pct=pct)

    if not result["has_alerts"]:
        return {"status": "skipped", "reason": "No alerts detected — spend is within threshold"}

    body = alert_email.build_email_html(result, pct, app_url)
    count = result["alert_count"]
    subject = f"Databricks Cost Alert — {count} issue{'s' if count != 1 else ''} detected"

    _send_or_500(smtp_host, smtp_port, smtp_user, smtp_pass, recipients, subject, body)

    return {
        "status": "sent",
        "to": recipients[0],
        "alert_count": count,
        "alerts": [a["title"] for a in result["alerts"]],
    }

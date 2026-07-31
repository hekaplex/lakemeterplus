"""
Standalone daily cost alert emailer — runs as a scheduled Databricks Job.

Detects spend spikes vs a 30-day rolling baseline and emails a summary.
Configure via environment variables (set as Databricks Job env vars or secrets).

Required env vars:
  DATABRICKS_HOST         workspace URL
  DATABRICKS_TOKEN        personal access token
  DATABRICKS_WAREHOUSE_ID SQL warehouse ID
  SMTP_USER               sender email (e.g. yourname@gmail.com)
  SMTP_PASSWORD           app password (Gmail: Settings -> App passwords)
  ALERT_EMAIL_TO          recipient(s), comma-separated

Optional env vars:
  SMTP_HOST               default: smtp.gmail.com
  SMTP_PORT               default: 587
  ALERT_THRESHOLD_PCT     spike threshold %, default: 20
  APP_URL                 app URL for "Open Dashboard" link in email
  MOCK_MODE               true/false (inherits from app env)

This script deliberately reuses the same spike-detection logic
(AlertService.detect_spikes, in ../services/alert_service.py) and the same
email template/sending code (../services/alert_email.py) that the FastAPI
app's own /alerts/send-now endpoint uses, rather than maintaining a second,
independent implementation of both — see
satsyil_lakemeterplus/docs/merge-tasks.md task #15. Run with the repo's
`src/backend` directory on PYTHONPATH (or as `python -m
app.observability.scripts.send_cost_alerts` from `src/backend`), same as
any other module in this app.
"""

from __future__ import annotations

import os
import sys

from databricks.sdk import WorkspaceClient

from app.observability.services.alert_service import AlertService
from app.observability.services import alert_email

# ── Config ────────────────────────────────────────────────────────────────────
HOST = os.environ["DATABRICKS_HOST"]
TOKEN = os.environ["DATABRICKS_TOKEN"]
# AlertService reads DATABRICKS_WAREHOUSE_ID itself via the shared Settings
# object (app.config.settings) — required here only so we fail fast with
# the same clear error if it's missing, before doing any work.
if not os.environ.get("DATABRICKS_WAREHOUSE_ID"):
    raise KeyError("DATABRICKS_WAREHOUSE_ID")
THRESHOLD = float(os.environ.get("ALERT_THRESHOLD_PCT", "20"))
APP_URL = os.environ.get("APP_URL", "")


def main() -> None:
    client = WorkspaceClient(host=HOST, token=TOKEN)
    svc = AlertService(client)

    print("Fetching spend data and detecting spikes...")
    result = svc.detect_spikes(threshold_pct=THRESHOLD)

    if not result["has_alerts"]:
        print("Spend is within threshold. No email sent.")
        sys.exit(0)

    print(f"Detected {result['alert_count']} alert(s).")

    try:
        smtp_host, smtp_port, smtp_user, smtp_pass, recipients = alert_email.read_smtp_config_from_env()
    except alert_email.SmtpConfigError as exc:
        print(f"SMTP configuration error: {exc}")
        sys.exit(1)

    body = alert_email.build_email_html(result, THRESHOLD, APP_URL)
    count = result["alert_count"]
    subject = f"Databricks Cost Alert — {count} issue{'s' if count != 1 else ''} detected"

    print(f"Sending email to {recipients}...")
    try:
        alert_email.send_email(smtp_host, smtp_port, smtp_user, smtp_pass, recipients, subject, body)
    except alert_email.EmailSendError as exc:
        print(f"Email send failed: {exc}")
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()

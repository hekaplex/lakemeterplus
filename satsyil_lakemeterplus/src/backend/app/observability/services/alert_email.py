"""Shared cost-alert email building and SMTP sending.

Extracted from routes/alerts.py so that both the FastAPI route (`/alerts/send-now`)
and the standalone scheduled-job script (scripts/send_cost_alerts.py) build and
send the same email from the same code, instead of two independently
hand-maintained HTML templates. See
satsyil_lakemeterplus/docs/merge-tasks.md task #15.

Deliberately framework-agnostic (raises plain exceptions, not
fastapi.HTTPException) so scripts/send_cost_alerts.py — which runs standalone
as a Databricks Job, outside the FastAPI app — can import it too.
"""
from __future__ import annotations

import html
import os
import re
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Allowed SMTP ports (reject arbitrary ports to prevent SSRF)
ALLOWED_SMTP_PORTS = {25, 465, 587, 2525}
# SMTP hosts must be a valid domain (prevent SSRF to internal IPs)
_SMTP_HOST_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$")


class SmtpConfigError(ValueError):
    """Raised when SMTP env vars are missing or invalid."""


class EmailSendError(RuntimeError):
    """Raised when the SMTP send itself fails (auth, connection, etc.)."""


def read_smtp_config_from_env() -> tuple[str, int, str, str, list[str]]:
    """Read and validate SMTP_* / ALERT_EMAIL_TO from the environment.

    Returns (host, port, user, password, recipients). Raises SmtpConfigError
    on missing/invalid config — callers translate that into whatever error
    shape fits their context (HTTPException for the API route, a printed
    message + sys.exit for the standalone script).
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    try:
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        raise SmtpConfigError("SMTP_PORT must be a valid integer")
    if smtp_port not in ALLOWED_SMTP_PORTS:
        raise SmtpConfigError(f"SMTP_PORT must be one of {sorted(ALLOWED_SMTP_PORTS)}")
    if not _SMTP_HOST_RE.match(smtp_host):
        raise SmtpConfigError("SMTP_HOST must be a valid domain name")

    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    alert_to_raw = os.environ.get("ALERT_EMAIL_TO", "")

    missing = [k for k, v in {"SMTP_USER": smtp_user, "SMTP_PASSWORD": smtp_pass, "ALERT_EMAIL_TO": alert_to_raw}.items() if not v]
    if missing:
        raise SmtpConfigError(f"Missing env vars: {', '.join(missing)}")

    # Basic recipient validation (mirrors core/validators.validate_email_address's
    # shape without importing the FastAPI-oriented validators module here).
    _email_re = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    recipients = []
    for addr in alert_to_raw.split(","):
        addr = addr.strip()
        if addr:
            if not _email_re.match(addr):
                raise SmtpConfigError(f"Invalid recipient email format: {addr}")
            recipients.append(addr)
    if not recipients:
        raise SmtpConfigError("ALERT_EMAIL_TO has no valid addresses")

    return smtp_host, smtp_port, smtp_user, smtp_pass, recipients


def send_email(
    smtp_host: str, smtp_port: int, smtp_user: str, smtp_pass: str,
    recipients: list[str], subject: str, html_body: str,
) -> None:
    """Send an HTML email with enforced TLS. Raises EmailSendError on failure."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject[:200]  # Truncate to prevent header injection
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailSendError("SMTP authentication failed") from exc
    except smtplib.SMTPException as exc:
        raise EmailSendError(f"Email delivery failed: {exc}") from exc
    except Exception as exc:
        raise EmailSendError(f"Email delivery failed: {exc}") from exc


def build_email_html(result: dict, threshold_pct: float, app_url: str) -> str:
    """Render an AlertService.detect_spikes() result dict as an HTML email body."""
    s = result.get("summary", {})
    pct = s.get("pct_vs_baseline", 0)
    pct_color = "#ff4444" if pct > 0 else "#00cc88"
    arrow = "&#x2191;" if pct > 0 else "&#x2193;"

    rows_html = ""
    for a in result.get("alerts", []):
        color = "#ff4444" if a["severity"] == "HIGH" else "#ffaa00"
        rows_html += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #2a2a3e;
                     color:{color};font-weight:bold;white-space:nowrap">{a['severity']}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #2a2a3e;font-weight:500">
            {html.escape(a['title'])}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #2a2a3e;color:#aaa">
            {html.escape(a['detail'])}</td>
        </tr>"""

    link = (f'<a href="{html.escape(app_url)}" '
            f'style="color:#FF3621;text-decoration:none">Open Dashboard &#x2192;</a>'
            if app_url else "")

    return f"""
    <html><body style="background:#13131f;color:#e0e0e0;font-family:Arial,sans-serif;
                       padding:32px;max-width:700px;margin:0 auto">
      <div style="margin-bottom:24px">
        <span style="color:#FF3621;font-size:22px;font-weight:bold">&#x26A0; Databricks Cost Alert</span>
        <span style="color:#555;font-size:13px;margin-left:12px">{result.get('generated_at', '')}</span>
      </div>

      <table style="width:100%;border-spacing:12px;border-collapse:separate;margin-bottom:24px">
        <tr>
          <td style="background:#1e1e30;border-radius:8px;padding:16px;text-align:center">
            <div style="color:#888;font-size:11px;letter-spacing:1px">30-DAY SPEND</div>
            <div style="font-size:26px;font-weight:bold;margin-top:4px">
              ${s.get('total_30d', 0):,.2f}</div>
          </td>
          <td style="background:#1e1e30;border-radius:8px;padding:16px;text-align:center">
            <div style="color:#888;font-size:11px;letter-spacing:1px">7-DAY AVG/DAY</div>
            <div style="font-size:26px;font-weight:bold;margin-top:4px">
              ${s.get('recent_avg_daily', 0):,.2f}</div>
            <div style="color:{pct_color};font-size:13px">
              {arrow}{abs(pct):.1f}% vs baseline</div>
          </td>
          <td style="background:#1e1e30;border-radius:8px;padding:16px;text-align:center">
            <div style="color:#888;font-size:11px;letter-spacing:1px">ALERTS</div>
            <div style="font-size:26px;font-weight:bold;color:#ff4444;margin-top:4px">
              {result.get('alert_count', 0)}</div>
            <div style="color:#888;font-size:13px">threshold: {threshold_pct:.0f}%</div>
          </td>
        </tr>
      </table>

      <table style="width:100%;border-collapse:collapse;background:#1e1e30;border-radius:8px;
                    overflow:hidden">
        <thead>
          <tr style="background:#252540">
            <th style="padding:10px 8px;text-align:left;color:#888;font-size:12px">SEVERITY</th>
            <th style="padding:10px 8px;text-align:left;color:#888;font-size:12px">ALERT</th>
            <th style="padding:10px 8px;text-align:left;color:#888;font-size:12px">DETAIL</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>

      <p style="margin-top:24px;color:#555;font-size:12px">
        {link} &nbsp;&#xB7;&nbsp; Threshold: {threshold_pct:.0f}% above baseline
        &nbsp;&#xB7;&nbsp; Databricks Cost Observability
      </p>
    </body></html>"""


def build_test_email_html() -> str:
    return """
    <html><body style="font-family:Arial,sans-serif;padding:24px;background:#1a1a2e;color:#e0e0e0">
      <h2 style="color:#FF3621">&#x2705; Test Alert &#x2014; Databricks Cost Observability</h2>
      <p>SMTP is configured correctly. You will receive real alerts when cost spikes are detected.</p>
      <p style="color:#888;font-size:12px">Databricks Cost Observability &#x2014; Alert System</p>
    </body></html>
    """

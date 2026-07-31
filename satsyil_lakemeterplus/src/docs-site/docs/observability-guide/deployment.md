---
sidebar_position: 3
---

# Deployment & Configuration

The observability module shares Lakemeter's deployment pipeline — there is no
separate install step. Its configuration is layered on top of the same
`scripts/install.sh` / `scripts/databricks.yml` flow documented in the
[Admin Guide](../admin-guide/installer).

## Configuration values

| Setting | Installer flag | Env var (in the deployed app) | Default |
|---|---|---|---|
| Demo / mock data | `--mock-mode true\|false` | `MOCK_MODE` | `true` |
| SQL Warehouse ID | `--warehouse-id <id>` | `DATABRICKS_WAREHOUSE_ID` | *(none)* |
| Unity Catalog name | `--catalog-name <name>` | `UC_CATALOG_NAME` | `workspace` |
| Admin panel access | `--admin-users <emails>` | `ADMIN_USERS` | *(none)* |

Run `./scripts/install.sh` interactively and it will prompt for each of
these; pass `--non-interactive` with the flags above for scripted installs
(e.g. from CI — see `.github/workflows/deploy.yml` / `.gitlab-ci.yml`'s
`deploy` job).

### `MOCK_MODE`

When `true` (the default), every query against a `system.*` Unity Catalog
table is rewritten at query time to `workspace.mock_system_*` instead, so
the dashboards work immediately without real system-table access or a
configured SQL Warehouse. Switch to `false` once you have both:

1. A SQL Warehouse ID (`--warehouse-id`) the app's Service Principal can
   query with.
2. Unity Catalog system tables enabled on the workspace (see
   [Databricks docs: system tables](https://docs.databricks.com/en/admin/system-tables/index.html)).

### Access control

Unlike the rest of Lakemeter — which relies on Databricks Apps' own
SSO/forwarded-header identity with no separate allowlist — the
observability module has an additional, narrower gate:
`ObservabilityAllowlistMiddleware` enforces `ALLOWED_USERS` (if set) on
`/api/v1/observability/*` only. Leave `ALLOWED_USERS` empty (the default) to
allow any workspace-authenticated user; set it to a comma-separated email
list to restrict the module to specific users. This does **not** affect
access to the rest of Lakemeter (estimates, calculator, etc.) — see
[Merge Notes](./merge-notes) for why that scope was deliberately kept
narrow.

`ADMIN_USERS` is separate: it controls who can reach the module's `/admin`
endpoints (managing other users' tab/workspace access) and alert-management
endpoints (`/alerts/config`, `/alerts/test-email`, `/alerts/send-now`) —
independent of whether `ALLOWED_USERS` is set at all.

### Alert emails (optional)

If you want spend-spike email alerts, also configure (via Databricks App
secrets, not the installer):

- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD`
- `ALERT_EMAIL_TO` — comma-separated recipients
- `ALERT_THRESHOLD_PCT` — percent above the 30-day baseline that triggers an
  alert (default 20)
- `APP_URL` — included as an "Open Dashboard" link in alert emails

The same detection and email-building code runs whether triggered from the
API (`/alerts/send-now`) or from a scheduled Databricks Job running
`backend/app/observability/scripts/send_cost_alerts.py` — see
[Merge Notes](./merge-notes) for why that used to be two separate
implementations.

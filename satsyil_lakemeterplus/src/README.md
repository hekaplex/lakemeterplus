# satsyil_lakemeterplus — merged scaffold

This is a **work-in-progress merge** of `lakemeter-oss` (cost estimation) and
`databricks-cost-observability` (cost/governance observability) into one
Databricks App. See `../docs/` for the architecture diagrams, feature
comparison, and full merge task plan this scaffold implements against
(`../docs/merge-tasks.md` now carries a Status column per task).
Remaining work is tracked in `../docs/TODO.md`. Licensing: see
`../LICENSE` and `../NOTICE.md`.

## What's here

- **`backend/app/`** — the host app, copied from `lakemeter-oss-main/backend/app`
  (FastAPI + SQLAlchemy + Lakebase, React SPA served from `static/` in
  production). This owns estimates, line items, workload calculators, the
  AI assistant, and export.
- **`backend/app/config.py`** — the **single, unified `Settings` class** for
  the whole app. Originally Lakemeter's own config, extended with all of
  the observability module's fields (`MOCK_MODE` is handled separately —
  see below — plus `DATABRICKS_WAREHOUSE_ID`, `ALLOWED_USERS`,
  `ADMIN_USERS`, `ALLOWED_WORKSPACE_IDS`, cloud-cost credentials, SMTP/alert
  vars, etc.) and their property helpers (`admin_users_set`,
  `user_configs_dict`, ...).
- **`backend/app/observability/`** — the **ported cost-observability module**,
  namespaced as its own Python package so it can't collide with Lakemeter's
  code:
  - `observability/core/config.py` — **not** a second settings class; a thin
    shim where `get_settings()` returns the same instance as
    `app.config.settings`, so the module's ~14 files that import
    `get_settings()` from here didn't need individual rewrites.
  - `observability/core/{dependencies,security,sql_executor,subscriptions,validators}.py` —
    ported from `databricks-cost-observability-main/core/`, imports rewritten.
    `security.py`'s `HTTPSRedirectMiddleware`, `SecurityHeadersMiddleware`,
    and `AuditLogMiddleware` are wired into `main.py`, app-wide.
  - `observability/routes/` — the 20 `api/v1/*.py` routers, ported.
  - `observability/services/` — the 18 `services/*.py` business-logic modules, ported.
  - `observability/router.py` — aggregates all of the above into one `api_router`,
    each sub-router keeping its own prefix (`/cost`, `/executive`, `/admin`, ...)
    under a shared `/observability` prefix.
  - `observability/scripts/` — mock/demo data generators (`setup_mock_tables.py`,
    `setup_enterprise_mock_data.py`, `send_cost_alerts.py`). The hardcoded
    demo warehouse ID these originally fell back to
    (`21f5bd20b7f44a51`) was removed — `DATABRICKS_WAREHOUSE_ID` is now a
    required env var here, same as `DATABRICKS_HOST`/`DATABRICKS_TOKEN`.
  - `observability/notebooks/` — cloud-cost ingestion and data-loading notebooks, ported as-is.
- **`backend/app/auth/databricks_auth.py`** and
  **`backend/app/observability/core/dependencies.py`** — still two separate
  identity-resolution code paths (see below), but their proxy-header lists
  (`EMAIL_HEADERS`/`USER_HEADERS` vs. `_USER_HEADERS`) were extended to the
  **union** of both, closing a real bug where a user's identity could
  silently resolve to empty in one module depending on which header
  Databricks Apps happened to send.
- **`backend/app/main.py`** — Lakemeter's original entrypoint, with:
  `app.include_router(observability_router, prefix="/api/v1")` (observability
  live at `/api/v1/observability/*`), plus the three security middlewares
  above added app-wide, outermost-to-innermost ahead of CORS.
- **`frontend/`** — Lakemeter's React/TS/Vite SPA. One observability page
  added as a proof of concept: `frontend/src/pages/Observability.tsx` (KPI
  cards from `/api/v1/observability/cost/summary`, raw JSON preview of
  `/api/v1/observability/executive/summary`), `frontend/src/api/observability.ts`
  (typed client), a `/observability` route, and a nav entry in `Layout.tsx`.
  The other ~16 observability domains have no frontend yet.
- **`scripts/`, `pyproject.toml`, `requirements.txt`, `backend/app.yaml`** —
  Lakemeter's installer/DAB/deployment files, with the observability
  module's Python dependencies (`scikit-learn`, `numpy`) and environment
  variables (`MOCK_MODE`, `ALLOWED_USERS`, `ADMIN_USERS`, SMTP/alert vars,
  etc.) merged in. Hardcoded environment-specific values found in the
  source repos (a specific workspace URL, the demo warehouse ID) were
  **removed and replaced with placeholders** rather than carried forward —
  fill them in per deployment. `scripts/databricks.yml` (the DAB) itself is
  still Lakemeter's original, unmerged with cost-observability's simpler
  bundle — see TODO.

## What is deliberately *not* merged (yet)

- **Data-access layers stay separate**: the observability module talks to
  Unity Catalog `system.*` tables via the Databricks SDK Statement Execution
  API; Lakemeter talks to Lakebase via SQLAlchemy. These are intentionally
  **not** being unified into one data layer — see `../docs/merge-tasks.md`
  ("Explicitly out of scope").
- **Identity resolution stays two functions**: header lists are unified (see
  above), but Lakemeter's DB-backed `get_or_create_user()` and the
  observability module's stateless `resolve_user_identity()` are still
  separate code paths, not one shared resolver.
- **Authorization gating stays scoped to `/observability/*`**:
  `ALLOWED_USERS`/`ADMIN_USERS` are on the unified `Settings`, but
  cost-observability's actual authz gate (`AllowlistMiddleware`) was
  deliberately **not** applied app-wide — doing so would change access
  control for Lakemeter's own estimation routes too, which is a product
  decision, not a mechanical port.

See `../docs/TODO.md` for the full remaining list.

## Verified so far

- Every ported `.py` file compiles (`python -m py_compile`).
- **Verified by actually running it**: installed both modules' dependencies
  into a scratch virtualenv and imported `app.main` for real
  (`PYTHONPATH=. python3 -c "import app.main"`). It imports cleanly.
  `app.openapi()` reports **136 total routes**, **48** of them under
  `/api/v1/observability/*`, zero prefix collisions with Lakemeter's own
  routes. `app.user_middleware` reports the expected stack:
  `['HTTPSRedirectMiddleware', 'SecurityHeadersMiddleware', 'AuditLogMiddleware', 'CORSMiddleware']`.
  `app.observability.core.config.get_settings() is app.config.settings`
  returns `True`, confirming the config shim actually shares one instance
  rather than silently parsing the environment twice.
- **Not verified**: an actual live request against any observability
  endpoint (needs `MOCK_MODE=true` + a real or mock SQL Warehouse +
  Databricks SDK auth), Lakemeter's own Lakebase connection (needs a real
  Postgres/Lakebase instance), and the frontend build — **no Node.js/npm
  was available in this environment**, so `frontend/src/pages/Observability.tsx`
  and `frontend/src/api/observability.ts` were written carefully against
  the existing code's conventions and reviewed by hand, but not compiled
  with `tsc`/Vite. Run `cd frontend && npm install && npm run build` before
  trusting them.

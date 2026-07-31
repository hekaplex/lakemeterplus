# satsyil_lakemeterplus — merged scaffold

This is a **work-in-progress merge** of `lakemeter-oss` (cost estimation) and
`databricks-cost-observability` (cost/governance observability) into one
Databricks App. See `../docs/` for the architecture diagrams, feature
comparison, and full merge task plan this scaffold implements against.
Remaining work is tracked in `../docs/TODO.md`.

## What's here

- **`backend/app/`** — the host app, copied from `lakemeter-oss-main/backend/app` as-is
  (FastAPI + SQLAlchemy + Lakebase, React SPA served from `static/` in
  production). This owns estimates, line items, workload calculators,
  the AI assistant, and export.
- **`backend/app/observability/`** — the **ported cost-observability module**,
  namespaced as its own Python package so it can't collide with Lakemeter's
  code:
  - `observability/core/` — `config.py`, `dependencies.py`, `security.py`,
    `sql_executor.py`, `subscriptions.py`, `validators.py` (all ported
    verbatim from `databricks-cost-observability-main/core/`, imports rewritten)
  - `observability/routes/` — the 20 `api/v1/*.py` routers, ported verbatim
  - `observability/services/` — the 18 `services/*.py` business-logic modules, ported verbatim
  - `observability/router.py` — aggregates all of the above into one `api_router`,
    each sub-router keeping its own prefix (`/cost`, `/executive`, `/admin`, ...)
    under a shared `/observability` prefix
  - `observability/scripts/` — mock/demo data generators (`setup_mock_tables.py`,
    `setup_enterprise_mock_data.py`), ported verbatim
  - `observability/notebooks/` — cloud-cost ingestion and data-loading notebooks, ported verbatim
- **`backend/app/main.py`** — Lakemeter's original entrypoint, with one addition:
  `app.include_router(observability_router, prefix="/api/v1")`, so the
  observability module is live at `/api/v1/observability/*` alongside
  Lakemeter's existing `/api/v1/*` routes.
- **`frontend/`** — Lakemeter's React/TS/Vite SPA, copied as-is. **Not yet
  extended** with observability pages/nav — see TODO.
- **`scripts/`, `pyproject.toml`, `requirements.txt`, `backend/app.yaml`** —
  Lakemeter's installer/DAB/deployment files, with the observability
  module's Python dependencies (`scikit-learn`, `numpy`) and environment
  variables (`MOCK_MODE`, `ALLOWED_USERS`, `ADMIN_USERS`, SMTP/alert vars,
  etc.) merged in. Hardcoded environment-specific values found in the
  source repos (a specific workspace URL, a demo warehouse ID) were
  **removed and replaced with placeholders** rather than carried forward —
  fill them in per deployment.

## What is deliberately *not* merged (yet)

The two modules keep **separate config, auth resolution, and data-access
layers** in this pass:

- `app.observability.core.config.Settings` is a distinct Pydantic settings
  class from Lakemeter's `app.config.settings` — both read from the process
  environment independently. Not unified yet (see TODO / merge-tasks.md #9).
- The observability module's identity resolution
  (`app.observability.core.dependencies.resolve_user_identity`, header-based)
  is separate from Lakemeter's `app.auth.databricks_auth`. They use
  overlapping but not-identical header names. Not unified yet (TODO / #7).
- The observability module talks to Unity Catalog `system.*` tables via the
  Databricks SDK Statement Execution API; Lakemeter talks to Lakebase via
  SQLAlchemy. These are intentionally **not** being unified into one data
  layer — see `../docs/merge-tasks.md` ("Explicitly out of scope").

This means the scaffold is **importable and route-complete, but not a fully
working merged deployment** — most observability endpoints will raise at
request time until config/auth are unified (they currently read the ported
module's own `Settings`, which has no values without its own env vars set).
See `../docs/TODO.md` for the concrete list of what's required to get it
fully running end-to-end.

## Verified so far

- Every ported `.py` file compiles (`python -m py_compile`) — no syntax
  errors or leftover unrewritten `core.`/`services.`/`api.v1` imports.
- No file path or route-prefix collisions between the two modules' routers.
- **Verified by actually running it**: installed both modules' dependencies
  into a scratch virtualenv and imported `app.main` for real
  (`PYTHONPATH=. python3 -c "import app.main"`). It imports cleanly and
  `app.openapi()` reports **136 total routes**, **48** of them under
  `/api/v1/observability/*` (e.g. `/api/v1/observability/cost/summary`,
  `/api/v1/observability/executive/summary`, `/api/v1/observability/admin/users`),
  alongside all of Lakemeter's original `/api/v1/*` routes — zero prefix
  collisions. This confirms the wiring in `main.py` and `observability/router.py`
  is correct, not just syntactically valid.
- Not verified: an actual live request against any observability endpoint
  (needs `MOCK_MODE=true` + a real or mock SQL Warehouse + Databricks SDK
  auth), and Lakemeter's own Lakebase connection (needs a real Postgres/Lakebase
  instance — the scaffold's `database.py` fails fast without one, as expected).

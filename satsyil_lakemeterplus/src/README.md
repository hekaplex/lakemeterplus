# satsyil_lakemeterplus — merged scaffold

This is a **work-in-progress merge** of `lakemeter-oss` (cost estimation) and
`databricks-cost-observability` (cost/governance observability) into one
Databricks App. See `../docs/` for the architecture diagrams, feature
comparison, and full merge task plan this scaffold implements against
(`../docs/merge-tasks.md` carries a Status column per task).
Remaining work is tracked in `../docs/TODO.md`. Licensing: see
`../LICENSE` and `../NOTICE.md`.

## What's here

- **`backend/app/`** — the host app, copied from `lakemeter-oss-main/backend/app`
  (FastAPI + SQLAlchemy + Lakebase, React SPA served from `static/` in
  production). This owns estimates, line items, workload calculators, the
  AI assistant, and export.
- **`backend/app/config.py`** — the **single, unified `Settings` class** for
  the whole app: Lakemeter's own config, extended with all of the
  observability module's fields (`DATABRICKS_WAREHOUSE_ID`, `ALLOWED_USERS`,
  `ADMIN_USERS`, `ALLOWED_WORKSPACE_IDS`, cloud-cost credentials, SMTP/alert
  vars, etc.) and their property helpers.
- **`backend/app/observability/`** — the **ported cost-observability module**,
  namespaced as its own Python package:
  - `observability/core/config.py` — a thin shim; `get_settings()` returns
    the same instance as `app.config.settings`, so the ~14 files that
    import it didn't need individual rewrites.
  - `observability/core/{dependencies,security,sql_executor,subscriptions,validators,allowlist}.py` —
    ported from `databricks-cost-observability-main`'s `core/` and `app.py`.
    `security.py`'s `HTTPSRedirectMiddleware`, `SecurityHeadersMiddleware`,
    `AuditLogMiddleware` are wired into `main.py` app-wide;
    `allowlist.py`'s `ObservabilityAllowlistMiddleware` enforces
    `ALLOWED_USERS`, but **only** on `/api/v1/observability/*` — see
    "What is deliberately not merged" below.
  - `observability/routes/` (20 files) and `observability/services/` (18
    files, plus `alert_email.py` — see task #15 below) — ported and wired.
  - `observability/router.py` — aggregates routes into one `api_router`
    under a shared `/observability` prefix.
  - `observability/scripts/` — mock/demo data generators and the
    standalone `send_cost_alerts.py` scheduled-job script (now reuses
    `AlertService` + `alert_email.py` instead of its own independent
    implementation — see task #15). The hardcoded demo warehouse ID these
    originally fell back to was removed in favor of a required env var.
  - `observability/notebooks/` — cloud-cost ingestion notebooks, ported as-is.
- **`backend/app/auth/databricks_auth.py`** and
  **`backend/app/observability/core/dependencies.py`** — still two separate
  identity-resolution code paths, but their proxy-header lists were
  extended to the **union** of both, closing a real bug where a user's
  identity could silently resolve to empty in one module depending on
  which header Databricks Apps sent.
- **`backend/app/main.py`** — Lakemeter's entrypoint, with the observability
  router mounted at `/api/v1/observability/*` and five middlewares added,
  outermost to innermost: `HTTPSRedirect → SecurityHeaders → AuditLog →
  ObservabilityAllowlist → CORS`.
- **`frontend/`** — Lakemeter's React/TS/Vite SPA. One observability page
  added as a proof of concept: `frontend/src/pages/Observability.tsx`,
  `frontend/src/api/observability.ts`, a `/observability` route, and a nav
  entry. The other ~16 observability domains have no frontend yet.
- **`scripts/`, `pyproject.toml`, `requirements.txt`, `backend/app.yaml`** —
  Lakemeter's installer/DAB/deployment files, dependencies and env vars
  unioned with the observability module's. Hardcoded environment-specific
  values found in the source repos were removed in favor of placeholders.
  `scripts/databricks.yml` (the DAB) is still Lakemeter's original,
  unmerged with cost-observability's simpler bundle — see TODO.
- **`tests/`** — a new test suite (26 tests) covering the merge work itself:
  route wiring, middleware order, config sharing, the observability
  allowlist's scoping, and (previously completely untested)
  `AlertService.detect_spikes()`'s spike-detection math. Does **not**
  include either source repo's own pre-existing test suite. Run with
  `python -m pytest` from `src/` (uses `pyproject.toml`'s
  `pythonpath = ["backend"]`).
- **`.github/workflows/ci.yml`** — compiles + runs the Python test suite,
  and builds the frontend, on every push/PR touching `src/`.

## What is deliberately *not* merged (yet)

- **Data-access layers stay separate**: the observability module talks to
  Unity Catalog `system.*` tables via the Databricks SDK Statement Execution
  API; Lakemeter talks to Lakebase via SQLAlchemy. Intentionally **not**
  unified — see `../docs/merge-tasks.md` ("Explicitly out of scope").
- **Identity resolution stays two functions**: header lists are unified,
  but Lakemeter's DB-backed `get_or_create_user()` and the observability
  module's stateless `resolve_user_identity()` are separate code paths.
- **Authorization gating stays scoped to `/observability/*`**:
  `ObservabilityAllowlistMiddleware` enforces `ALLOWED_USERS` only on
  observability routes — applying it (or an equivalent) to Lakemeter's own
  estimation routes too is a product decision, not made here.

See `../docs/TODO.md` for the full remaining list.

## Verified so far

Everything below was actually run, not just written and assumed correct.

- **Full test suite passes**: `python -m pytest` — 26/26 passed, including
  live `TestClient` requests through the whole middleware stack.
- **Merged app imports and serves cleanly**: installed dependencies into a
  scratch virtualenv, imported `app.main` for real. `app.openapi()`
  reports **136 total routes**, **48** under `/api/v1/observability/*`,
  zero collisions with Lakemeter's own routes.
- **Middleware stack verified live**: `app.user_middleware` reports
  `['HTTPSRedirectMiddleware', 'SecurityHeadersMiddleware', 'AuditLogMiddleware', 'ObservabilityAllowlistMiddleware', 'CORSMiddleware']`.
- **Config sharing verified live**:
  `app.observability.core.config.get_settings() is app.config.settings` → `True`.
- **Allowlist scoping verified with real requests, not just code review**:
  `GET /health` (Lakemeter) → 200 with no identity header;
  `GET /api/v1/observability/health/` → 200 public;
  `GET /api/v1/observability/cost/summary` with no identity → 403;
  same request with `X-Forwarded-User` set → passes the gate and reaches
  real service code (which then attempted an actual Databricks SQL
  Warehouse call and failed for environmental reasons — no `MOCK_MODE`
  configured in the test — not a wiring bug).
- **A real bug found and fixed**: 12 lazy/function-local imports across
  the observability module were missed by the original import-rewrite pass
  (it only matched imports at column 0) and still pointed at pre-merge
  module paths. Found by tracing a route through to its real implementation
  while working the alert-deduplication task, fixed, and re-verified with
  `TestClient` requests that no longer raise `ModuleNotFoundError`.
- **CI workflow YAML-validated** with `pyyaml`; not run through actual
  GitHub Actions (no such environment available here).

**Not verified**: an actual request against a real Databricks workspace or
Lakebase instance (needs real infrastructure), and the frontend build — **no
Node.js/npm was available in this environment**, so
`frontend/src/pages/Observability.tsx` and `frontend/src/api/observability.ts`
were written carefully by hand against existing conventions but not
compiled with `tsc`/Vite. Run `cd frontend && npm install && npm run build`
before trusting them — treat the frontend changes as meaningfully
higher-risk than everything else in this scaffold.

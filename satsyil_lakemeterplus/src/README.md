# satsyil_lakemeterplus — merged scaffold

This is a **work-in-progress merge** of `lakemeter-oss` (cost estimation) and
`databricks-cost-observability` (cost/governance observability) into one
Databricks App. See `../docs/` for the architecture diagrams, feature
comparison, and full merge task plan this scaffold implements against
(`../docs/merge-tasks.md` carries a Status column per task — **18 of 24
done, 4 partial, 2 not started**). Remaining work is tracked in
`../docs/TODO.md`. Licensing: see `../LICENSE` and `../NOTICE.md`.

## What's here

- **`backend/app/`** — the host app, copied from `lakemeter-oss-main/backend/app`
  (FastAPI + SQLAlchemy + Lakebase, React SPA served from `static/` in
  production). This owns estimates, line items, workload calculators, the
  AI assistant, and export.
- **`backend/app/config.py`** — the **single, unified `Settings` class** for
  the whole app: Lakemeter's own config, extended with all of the
  observability module's fields.
- **`backend/app/observability/`** — the **ported cost-observability module**,
  namespaced as its own Python package:
  - `observability/core/config.py` — a thin shim; `get_settings()` returns
    the same instance as `app.config.settings`.
  - `observability/core/{dependencies,security,sql_executor,subscriptions,validators,allowlist}.py` —
    ported from `databricks-cost-observability-main`'s `core/` and `app.py`.
    `security.py`'s three middlewares are wired into `main.py` app-wide;
    `allowlist.py`'s `ObservabilityAllowlistMiddleware` enforces
    `ALLOWED_USERS`, but **only** on `/api/v1/observability/*`.
  - `observability/models.py` — `ObservabilityUserPermission`, a SQLAlchemy
    model against Lakebase (table `lakemeter.observability_user_permissions`).
    Migrated off Delta-table storage — see `services/user_permissions_service.py`.
  - `observability/routes/` (20 files) and `observability/services/` (18
    files, plus `alert_email.py`) — ported and wired.
  - `observability/router.py` — aggregates routes under a shared
    `/observability` prefix.
  - `observability/scripts/` — mock/demo data generators and the
    standalone `send_cost_alerts.py` scheduled-job script (reuses
    `AlertService` + `alert_email.py` rather than its own independent
    implementation).
  - `observability/notebooks/` — cloud-cost ingestion notebooks, ported as-is.
- **`backend/app/auth/databricks_auth.py`** and
  **`backend/app/observability/core/dependencies.py`** — still two separate
  identity-resolution code paths, but their proxy-header lists were
  unioned, closing a bug where identity could silently resolve to empty in
  one module depending on which header Databricks Apps sent.
- **`backend/app/main.py`** — Lakemeter's entrypoint, with the observability
  router mounted at `/api/v1/observability/*` and five middlewares added,
  outermost to innermost: `HTTPSRedirect → SecurityHeaders → AuditLog →
  ObservabilityAllowlist → CORS`.
- **`frontend/`** — Lakemeter's React/TS/Vite SPA. One observability page
  as a proof of concept (`Observability.tsx` + `api/observability.ts` + a
  route + a nav entry). The other ~10 observability domains have no
  frontend yet — see `../docs/TODO.md`, this is the least-verified part of
  the whole merge (no Node.js was available to build/type-check it).
- **`docs-site/`** — Lakemeter's Docusaurus documentation site (this
  hadn't been ported into `src/` before this merge at all). Static
  walkthrough video/GIF media (36MB) was deliberately excluded; the docs
  themselves and a new **Cost Observability** section
  (`docs/observability-guide/`) are included.
- **`scripts/`** — `databricks.yml` (the DAB), `notebooks/`, `functions/`,
  and `install.sh` (the interactive/scripted installer entrypoint, ported
  and extended for the observability module's config — see the note on
  `install_lakemeter.py` below).
- **`tests/`** — **115 tests, all passing**, covering the merge work
  itself: route wiring, middleware order, config sharing, the
  observability allowlist's scoping (and a real auth-ordering bug it
  exposed during the Lakebase migration), `AlertService`'s spike-detection
  math, `CostService`'s IDOR-protecting WHERE-clause builder,
  `ExecutiveService`'s fiscal-year date math, SQL-injection validators,
  the `MOCK_MODE` rewrite logic, and real CRUD round-trips for the
  migrated permissions service. Does **not** include either source repo's
  own pre-existing test suite. Run with `python -m pytest` from `src/`.
- **`.github/workflows/ci.yml`** / **`.gitlab-ci.yml`** — compile + test +
  frontend build, on every push/PR. Functionally equivalent to each other.
- **`.github/workflows/deploy.yml`** (and its GitLab-CI job of the same
  name) — deploys the bundle and runs the installer job. Structurally
  avoids a bug present in cost-observability's original `deploy.yml` (a
  hardcoded `/dev/` bundle path used regardless of the selected target).

## What is deliberately *not* merged (yet)

- **Data-access layers stay mostly separate**: the observability module's
  dashboards talk to Unity Catalog `system.*` tables via the Databricks
  SDK Statement Execution API; Lakemeter talks to Lakebase via SQLAlchemy.
  The one exception is the observability module's own per-user permission
  store, migrated onto Lakebase (see `models.py` above) — everything else
  stays on its original data path.
- **Identity resolution stays two functions**: header lists are unified,
  but Lakemeter's DB-backed `get_or_create_user()` and the observability
  module's stateless `resolve_user_identity()` are separate code paths.
- **Authorization gating stays scoped to `/observability/*`**: extending
  it (or something like it) to Lakemeter's own estimation routes is a
  product decision, not made here.
- **`install_lakemeter.py`** (the source repo's *other* installer
  implementation, overlapping with `install.sh`) was not ported —
  `install.sh` was chosen as authoritative because its task-key list and
  `--params` already matched the merged `databricks.yml`/notebooks. This
  was a judgment call made in this session, not a decision either source
  repo had already settled.

See `../docs/TODO.md` for the full remaining list.

## Verified so far

Everything below was actually run, not just written and assumed correct.

- **Full test suite passes**: `python -m pytest` — **115/115 passed**,
  including live `TestClient` requests through the whole middleware stack
  and real CRUD round-trips against an isolated in-memory SQLite database
  (for the Lakebase-migrated permissions service — SQLite doesn't support
  Postgres schemas natively, so this required `ATTACH DATABASE ':memory:'
  AS lakemeter` + `StaticPool`, verified empirically before being written
  as a test fixture).
- **Merged app imports and serves cleanly**: `app.openapi()` reports
  **136 total routes**, **48** under `/api/v1/observability/*`, zero
  collisions with Lakemeter's own routes.
- **Middleware stack, config sharing, and allowlist scoping** all verified
  live (not just by code review) — see git history of this file or
  `../docs/merge-tasks.md` tasks #5, #8, #9, #22 for the exact assertions.
- **Two real bugs found and fixed during this merge, both now pinned by
  tests**:
  1. 12 lazy/function-local imports across the observability module were
     missed by the original mechanical import-rewrite pass (it only
     matched imports at column 0) and still pointed at pre-merge module
     paths — would have raised `ModuleNotFoundError` the first time
     specific routes executed.
  2. Migrating `UserPermissionsService` to take `db: Session =
     Depends(get_db)` meant FastAPI could resolve (and 503 on) that
     dependency *before* the in-body `require_admin()` admin check ran —
     a non-admin could get a 503 instead of a 403 when the database was
     down. Fixed by making `require_admin` itself a `Depends()` parameter,
     ordered first.
- **Generated `app.yaml` verified by rendering the actual template**:
  `scripts/notebooks/05a_create_app.py`'s `app_yaml_content` f-string
  (dbutils isn't available outside a real Databricks notebook, so the
  notebook can't run locally) was rendered with realistic sample values
  in a throwaway script and the output confirmed as valid YAML with
  exactly the expected observability env vars in the right places.
- **All YAML configs validated, shell scripts syntax-checked**: `ci.yml`,
  `deploy.yml`, `.gitlab-ci.yml`, `scripts/databricks.yml` all parse with
  `pyyaml`; `deploy.yml`, the GitLab deploy job, and `scripts/install.sh`
  all pass `bash -n`. None run through their actual CI platform.
- **Docs-site new content validated**: all 4 new `observability-guide/`
  pages' YAML frontmatter parses and every image path they reference
  actually exists on disk (checked programmatically); `sidebars.ts`/
  `docusaurus.config.ts` edits are bracket-balanced (no Node.js available
  to run an actual Docusaurus build — same limitation as the React work).

**Not verified, at any point in this merge**: an actual request against a
real Databricks workspace or Lakebase instance (needs real infrastructure),
and anything requiring a JavaScript/TypeScript toolchain — no Node.js was
available in this environment. Every frontend-adjacent change (the
Observability page, its API client, the docs-site port and its new pages,
the `sidebars.ts`/`docusaurus.config.ts` edits) was written carefully by
hand and checked as thoroughly as possible without one, but none of it has
been compiled or type-checked. Treat that as meaningfully higher-risk than
the backend work, all of which was verified by actually executing it.

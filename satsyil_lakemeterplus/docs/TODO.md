# TODO — Remaining Merge Work

Status snapshot of `satsyil_lakemeterplus/src` against the plan in
`merge-tasks.md` (which carries a Status column per task). This file is
the narrative version, and records what was actually verified — imported,
tested, or hand-reviewed — rather than just written and assumed correct.

Of the 24 tasks in `merge-tasks.md`: **13 done, 5 partial, 6 not started.**
All 6 P0 tasks are done. All P1 tasks are done or partial. Every "done"/
"partial" claim below was checked by actually running code (a real
`pytest` run, a live `TestClient` request cycle, a rendered-template YAML
parse, a `bash -n` syntax check) — see each task's entry for exactly what
was run.

## Done / partial (this session)

**Backend scaffold + wiring (tasks 2–6, done):** `src/backend` = copy of
`lakemeter-oss`'s backend source; `src/frontend` = copy of its React SPA
source. `databricks-cost-observability`'s 20 routers, 18 services, and
`core/` infra were ported into `src/backend/app/observability/`. Verified
by importing the merged app: 136 total routes, 48 under
`/api/v1/observability/*`, zero collisions.

**Config unification (task 9, done):** one `Settings` class backs both
modules; `app/observability/core/config.py` is a shim returning the same
instance. Verified at runtime and pinned by a test.

**Auth header unification (task 7, partial):** the two modules' proxy
header lists were extended to their union, closing a bug where one module
could silently see no identity depending on which header Databricks Apps
sent. The two modules still run separate resolver functions.

**Observability access control (task 8, partial):**
`ObservabilityAllowlistMiddleware` enforces `ALLOWED_USERS` on
`/api/v1/observability/*` only. Verified with live `TestClient` requests
through the full middleware stack, not just code review: Lakemeter's
`/health` unaffected, the observability health check public, an
unauthenticated observability request 403s, an authenticated one passes
the gate and reaches real service code.

**Security middleware (task 22, done):** `HTTPSRedirectMiddleware`,
`SecurityHeadersMiddleware`, `AuditLogMiddleware` wired in app-wide, order
verified and pinned by a test.

**A real bug found and fixed:** the original mechanical import rewrite
missed 12 lazy/function-local imports across the observability module
(indented, so the column-0-anchored `sed` pattern skipped them) — they
still pointed at pre-merge module paths and would have raised
`ModuleNotFoundError` the first time a user hit `/user/config`, any
`/admin/*` route, `/alerts/summary`, or several others. Fixed and
re-verified with live requests that no longer error that way.

**Alert logic de-duplication (task 15, done):** extracted
`app/observability/services/alert_email.py`; the standalone scheduled-job
script now reuses `AlertService` instead of an independent (and less
complete) reimplementation, gaining `MOCK_MODE` support for free.

**Deployment DAB merge (task 13, partial):** `scripts/databricks.yml`
gained a `variables:` block (`warehouse_id`, `catalog_name`, `mock_mode`,
`admin_users`) and `dev`/`prod` targets, threaded into
`scripts/notebooks/05a_create_app.py` — the notebook that actually
generates the deployed app's `app.yaml` (not the static
`backend/app.yaml`, which is a separate reference copy for local/manual
use). That notebook now writes all the observability module's env vars
into the generated config. Deliberately **not** merged: cost-observability's
declarative `resources.apps:` bundle resource — Lakemeter's app is created
imperatively via SDK calls in a notebook, and declaring both would fight
over ownership of the same app resource. **Not ported at all**: the
`install.sh` / `scripts/install.sh` / `scripts/install_lakemeter.py`
installer entrypoints — only `databricks.yml`, `notebooks/`, and
`functions/` were copied into `src/scripts/`. Verified: rendered the
notebook's `app_yaml_content` f-string template with realistic sample
values in a throwaway script and confirmed the output is valid YAML with
exactly the expected env vars; the bundle YAML itself was parsed and its
parameter/target wiring inspected structurally.

**CI + deploy workflows (tasks 19 & 24, done):**
`src/.github/workflows/ci.yml` (compile + `pytest -v` + frontend build) and
`src/.github/workflows/deploy.yml` (bundle deploy + installer job run).
The deploy workflow structurally avoids cost-observability's known
dev/prod bundle-path bug by never manually constructing a
target-specific path at all. Both YAML- and (for deploy.yml) shell-syntax
validated; neither run through actual GitHub Actions.

**Test suite (task 18, partial):** `src/tests/` — **77 tests, all
passing**, run for real via `python -m pytest`: the merge-wiring tests
from earlier in this session, plus (this round) `test_validators.py`
(the module's primary SQL-injection defense, including explicit
injection-payload rejection cases) and `test_sql_executor.py` (the
`MOCK_MODE` table-rewrite regex that powers demo mode) — both previously
at zero coverage. Not covered: unit tests for ~13 remaining observability
services; neither source repo's own test suite was ported in.

**Hardcoded values removed (task 11, done); `requirements.txt`/`app.yaml`
merged (tasks 9/14, done); licensing resolved (task 1, done — Elastic
License 2.0 per explicit user decision, see `../LICENSE`/`../NOTICE.md`,
good-faith reading not legal advice); frontend proof of concept (task 12,
partial, unverified by a build — no Node.js available this session).**
Unchanged from the previous round — see git history / prior state of this
file for the detailed verification notes on each.

## Not started / explicitly deferred

| # | Task | Why it's not done | Recommended next step |
|---|---|---|---|
| 8 (remainder) | Decide whether `ALLOWED_USERS`/`ADMIN_USERS` should also gate Lakemeter's own routes | Product decision, not an engineering one | Get the decision, then extend or leave `ObservabilityAllowlistMiddleware`'s scope |
| 12 (remainder) | Frontend pages for the other ~16 observability domains | Largest remaining piece of work by volume; also the least-verified part of the merge (no Node.js available) | Incremental delivery, one domain per page; get a real `npm run build` run before extending further |
| 13 (remainder) | Port `install.sh`/`scripts/install.sh`/`scripts/install_lakemeter.py` into `src/`; reconcile which is authoritative (the source repo itself has two overlapping installer implementations) | Not attempted — larger scope than the DAB/notebook wiring done this session | Needs a decision on which installer path is authoritative before porting either |
| 16 | Migrate `UserPermissionsService` off Delta tables onto Lakebase | Not started (P2, optional) | Only worth it if there's appetite for a schema migration |
| 17 | Reconcile SKU/product-type mapping duplication | Not started | Needs a design decision on whether estimation and observability should share one SKU-naming utility despite keeping separate pricing data sources |
| 18 (remainder) | Unit tests for `cost_service.py`, `executive_service.py`, and the other ~11 observability services; port either source repo's own test suite | Time-boxed to the highest-value previously-zero-coverage gaps (alert math, SQL-injection validators, mock-mode rewrite) plus the merge wiring itself | Follow the pattern in `src/tests/observability/`; `cost_service.py`/`executive_service.py` are the largest, most logic-heavy files and the natural next targets |
| 20 | Cross-link estimate-vs-actual comparison feature | Not started (net-new feature) | Worth a dedicated design doc once both modules are further along |
| 21 | Replace HTML-DOM-manifest smoke checks with component/E2E tests | Blocked on 12 (only one React observability page exists) | |
| 23 | Consolidate documentation sites | Not started (P3) | |

## Known gaps not captured as numbered merge-tasks

- **`src/backend/static/`** only contains the `pricing/` CSV bundle and the
  Databricks icon — the compiled React `assets/` bundle isn't checked in.
  Running in "combined" mode requires `cd src/frontend && npm install &&
  npm run build`, then copying `dist/` into `src/backend/static/`.
- **No end-to-end request against a real Databricks workspace or Lakebase
  instance was made.** The closest verification was a `TestClient` request
  that reached real SQL-execution code and failed only for environmental
  reasons — meaningfully stronger evidence than import-time checks alone,
  but still not a real deployment.
- **No Node.js was available in this environment**, so all frontend
  changes (task 12) are unverified by a build. Every backend change this
  session, by contrast, was verified by actually running Python code — a
  real `pytest` suite (77 tests), live `TestClient` request cycles through
  the full middleware stack, and rendered-template YAML validation for the
  generated `app.yaml` and both GitHub Actions workflows.
- **Neither GitHub Actions workflow (`ci.yml`, `deploy.yml`) has been run
  through actual GitHub Actions** — both were YAML- (and for `deploy.yml`,
  shell-) syntax validated locally, which catches structural errors but
  not e.g. missing repo secrets, permissions issues, or runner-environment
  differences.

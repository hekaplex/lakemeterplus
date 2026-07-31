# TODO — Remaining Merge Work

Status snapshot of `satsyil_lakemeterplus/src` against the plan in
`merge-tasks.md`. Task numbers below match that file, which carries a
**Status** column per task — this file is the narrative version, and
records what was actually verified (imported, tested, or hand-reviewed)
rather than just written.

## Done (this session, across two work passes)

**Backend scaffold + wiring (tasks 2–6, done):** `src/backend` = copy of
`lakemeter-oss`'s backend source; `src/frontend` = copy of its React SPA
source. `databricks-cost-observability`'s 20 routers, 18 services, and
`core/` infra were ported into `src/backend/app/observability/`. Verified
by actually importing the merged app: 136 total routes, 48 under
`/api/v1/observability/*`, zero collisions.

**Config unification (task 9, done):** one `Settings` class backs both
modules; `app/observability/core/config.py` is a shim returning the same
instance. Verified at runtime (`get_settings() is settings` → `True`) and
now pinned by `tests/test_merged_app_wiring.py`.

**Auth header unification (task 7, partial):** the two modules' proxy
header lists were extended to their union, closing a real bug where one
module could silently see no identity depending on which header Databricks
Apps sent. The two modules still run separate resolver functions — not a
single shared one.

**Observability access control (task 8, partial — new this pass):**
`app/observability/core/allowlist.py` (`ObservabilityAllowlistMiddleware`)
enforces `ALLOWED_USERS` on `/api/v1/observability/*` only, deliberately
scoped so it can't change access control for Lakemeter's own routes (that
remains a product decision, not resolved here). Verified with a live
`TestClient` request cycle, not just import-time checks: Lakemeter's
`/health` unaffected (200), the observability health check public (200),
an unauthenticated observability request correctly 403s, and an
authenticated one passes the gate and reaches the real service layer (it
then 400'd trying to reach a real Databricks profile found on this
machine — expected without `MOCK_MODE`, and itself proof the full
middleware → route → service → SDK pipeline executes correctly end to end).

**Security middleware (task 22, done):** `HTTPSRedirectMiddleware`,
`SecurityHeadersMiddleware`, `AuditLogMiddleware` wired in app-wide.
Verified stack order: `HTTPSRedirect → SecurityHeaders → AuditLog →
ObservabilityAllowlist → CORS`, now pinned by a test.

**A real bug found and fixed (new this pass):** while working the alert
de-duplication task, discovered that the original mechanical import
rewrite (`sed` with a `^from core\.` anchor) only matched imports at
column 0 — it missed **12 lazy, function-local imports** scattered across
`routes/user.py`, `routes/alerts.py`, `routes/admin.py` (×3),
`routes/ml_cost.py`, `routes/query.py`, `routes/compute.py`,
`routes/access.py`, and `services/user_permissions_service.py` (×2),
`services/storage_service.py` — all still pointing at the pre-merge
`core.`/`services.` module paths that no longer exist. These wouldn't have
shown up in earlier import-time verification (they're inside function
bodies, only triggered when those specific code paths execute) — they
would have raised `ModuleNotFoundError` the first time a user hit
`/user/config`, `/alerts/summary`, any `/admin/*` route, or the
account-level branches of `/cost/ml-anomalies`, `/platform/query-insights`,
`/platform/compute-insights`, or `/platform/access-governance`. All fixed
with a whitespace-aware `sed` pass and re-verified: every one of those
routes now reaches its real handler logic (confirmed via `TestClient`,
checking tracebacks no longer mention `ModuleNotFoundError` or the old
module paths).

**Alert logic de-duplication (task 15, done):** extracted
`app/observability/services/alert_email.py` (SMTP validation, sending,
HTML templating) out of `routes/alerts.py`. `scripts/send_cost_alerts.py`
(the standalone scheduled-job script) now imports `AlertService` +
`alert_email` directly instead of maintaining its own independent SQL
rewriter, spike-detection math, and email template — and picked up
`MOCK_MODE` support for free in the process (it previously reimplemented
that separately, and incompletely). Verified: the script imports cleanly
with no accidental Lakebase/SQLAlchemy side effects, and the refactored
`/alerts/*` routes still respond correctly.

**Test suite (task 18, partial — new this pass):** `src/tests/` — 26 tests,
**all run and passing** via `python -m pytest` (not just written):
- `test_merged_app_wiring.py` — route-collision, route-prefix, middleware-order,
  and config-sharing regression tests (codifies checks that were previously
  only done by hand).
- `observability/test_allowlist.py` — behavioral pin for task #8's scoping.
- `observability/test_alert_service.py` — unit tests for
  `AlertService.detect_spikes()`'s baseline/spike/new-SKU/growth math,
  monkeypatching the SQL fetch methods. This logic had **zero** prior test
  coverage in either source repo.
- `observability/test_alert_email.py` — SMTP config validation and HTML
  template rendering/XSS-escaping.

Not covered: unit tests for the other 17 observability services, and
neither source repo's own test suite was ported in.

**CI workflow (task 19, done — new this pass):** `src/.github/workflows/ci.yml`
— a `python-checks` job (compile + `pytest -v`) and a `frontend-build` job
(`npm ci && npm run build`), adapted from Lakemeter's own `ci.yml`.
YAML-validated with `pyyaml`; not run through actual GitHub Actions (no
such environment available here).

**Hardcoded values removed (task 11, done):** the demo warehouse ID
`21f5bd20b7f44a51` that silently defaulted three scripts was replaced with
a required environment variable.

**`requirements.txt` / `app.yaml` merge (tasks 9/14, done):** dependency
lists unioned; `app.yaml` env vars unioned; hardcoded environment-specific
values (a workspace URL, the demo warehouse ID) replaced with placeholders.

**Licensing (task 1, done):** per explicit user decision, Elastic License
2.0 (the more permissive of the two upstream licenses — it doesn't tie use
to being a customer of a specific vendor's paid service, unlike the
Databricks License) was adopted for the merged code. Implemented as
`../LICENSE` + `../NOTICE.md` (preserving both upstreams' required
attribution). **Good-faith technical reading, not legal advice** — get it
reviewed before any distribution beyond internal/scaffold use.

**Frontend proof of concept (task 12, partial):** one observability page
(`src/frontend/src/pages/Observability.tsx`), a typed API client, route,
and nav entry. **Not verified by a build** — no Node.js/npm was available
in this environment; written carefully by hand against existing
conventions but should be treated as higher-risk than the backend changes
until someone runs `npm install && npm run build`.

## Not started / explicitly deferred

| # | Task | Why it's not done | Recommended next step |
|---|---|---|---|
| 8 (remainder) | Decide whether `ALLOWED_USERS`/`ADMIN_USERS` should also gate Lakemeter's own routes | Product decision, not an engineering one | Get the decision, then either extend `ObservabilityAllowlistMiddleware`'s scope or leave it as-is |
| 12 (remainder) | Frontend pages for the other ~16 observability domains | Largest remaining piece of work by volume | Incremental delivery, one domain per page |
| 13 | Merge `databricks.yml` (DAB) | Not attempted | Add warehouse/catalog bundle variables + SQL Warehouse permissions as a parallel task in Lakemeter's existing 9-task DAG |
| 16 | Migrate `UserPermissionsService` off Delta tables onto Lakebase | Not started (P2, optional) | Only worth it if there's appetite for a schema migration |
| 17 | Reconcile SKU/product-type mapping duplication | Not started | Needs a design decision on whether estimation and observability should share one SKU-naming utility despite keeping separate pricing data sources |
| 18 (remainder) | Unit tests for the other 17 observability services; port either source repo's own test suite | Time-boxed this session to the highest-value gap (previously-zero-coverage alert math) plus the merge-wiring itself | Follow the same pattern established in `src/tests/observability/` |
| 20 | Cross-link estimate-vs-actual comparison feature | Not started (net-new feature) | Worth a dedicated design doc once both modules are further along |
| 21 | Replace HTML-DOM-manifest smoke checks with component/E2E tests | Blocked on 12 (only one React observability page exists) | |
| 23 | Consolidate documentation sites | Not started (P3) | |
| 24 | Write a deploy workflow for `src/`, avoiding cost-observability's known dev/prod bundle-path bug | CI (`ci.yml`) exists now; a deploy workflow does not | Base it on Lakemeter's simpler single-target deploy rather than cost-observability's dev/prod-path pattern |

## Known gaps not captured as numbered merge-tasks

- **No deploy workflow exists yet for `src/`** — CI (build/test) does now;
  actual deployment automation doesn't.
- **`src/backend/static/`** only contains the `pricing/` CSV bundle and the
  Databricks icon — the compiled React `assets/` bundle isn't checked in.
  Running in "combined" mode requires `cd src/frontend && npm install &&
  npm run build`, then copying `dist/` into `src/backend/static/`.
- **No end-to-end request against a real Databricks workspace or Lakebase
  instance was made.** The closest verification done was a `TestClient`
  request that reached real SQL-execution code and failed only for
  environmental reasons (see the task #8 entry above) — that's meaningfully
  stronger evidence than import-time checks alone, but it's still not a
  real deployment.
- **No Node.js was available in this environment**, so all frontend changes
  (task 12) are unverified by a build — treat them as higher-risk than the
  backend changes, which *were* verified by actually running Python code
  and a real pytest suite, not just written and assumed correct.

# TODO — Remaining Merge Work

Status snapshot of `satsyil_lakemeterplus/src` against the plan in
`merge-tasks.md`. Task numbers below match that file, which now carries a
**Status** column per task — this file is the narrative version.

## Done this session

**Backend scaffold + wiring (tasks 2–6):** `src/backend` = copy of
`lakemeter-oss`'s backend app source; `src/frontend` = copy of its React
SPA source. `databricks-cost-observability`'s 20 routers, 18 services, and
`core/` infra were ported into `src/backend/app/observability/`, imports
rewritten, and mounted in `main.py`. **Verified by actually installing
dependencies and importing `app.main`** (not just `py_compile`): the merged
app reports 136 total routes via `app.openapi()`, 48 of them under
`/api/v1/observability/*`, zero path collisions with Lakemeter's own routes.

**Config unification (task 9, done):** all of the observability module's
settings fields and property helpers were folded into `app/config.py`'s
`Settings` class. `app/observability/core/config.py` is now a compatibility
shim — `get_settings()` returns the *same* `app.config.settings` instance —
so the ~14 files that import it didn't need individual rewrites. Verified
at runtime: `app.observability.core.config.get_settings() is app.config.settings`
→ `True`.

**Auth header unification (task 7, partial):** the two modules used
different, non-overlapping sets of proxy header names for the same
Databricks Apps identity (Lakemeter: `X-Forwarded-Email`; observability:
`x-forwarded-user`, `x-databricks-user-email`, etc.). This was a real bug
risk post-merge — one module could silently see no identity depending on
which header Databricks Apps sent. Fixed by extending both header lists to
their union. **Still separate:** the two modules keep their own resolver
functions and identity-of-record concept (Lakemeter's DB-backed `User` row
vs. observability's stateless per-request resolution) — collapsing those
into one shared resolver is still open.

**Security middleware (task 22, done):** `HTTPSRedirectMiddleware`,
`SecurityHeadersMiddleware`, and `AuditLogMiddleware` (rate limiting, bot
detection, IP banning) from the observability module are now wired into
`main.py` app-wide. Deliberately **not** ported: `AllowlistMiddleware`,
cost-observability's actual authz gate — applying that app-wide would
change access control for Lakemeter's own estimation routes too, which is
a product decision, not a mechanical port (see task 8, still open).

**Hardcoded values removed (task 11, done):** the demo warehouse ID
`21f5bd20b7f44a51` that appeared as a silent fallback default in three
scripts (`send_cost_alerts.py`, `setup_mock_tables.py`,
`setup_enterprise_mock_data.py`) was replaced with a required environment
variable, matching how `DATABRICKS_HOST`/`DATABRICKS_TOKEN` already behave
in those same scripts. (Left untouched: the same ID string used as
self-consistent mock *data* — seeding a fake warehouse row — inside
`setup_mock_tables.py`; that's demo content, not configuration.)

**`requirements.txt` / `app.yaml` merge (task 9/14, done):** dependency
lists unioned (`scikit-learn`, `numpy` added). `app.yaml` env vars unioned;
the two source repos' hardcoded environment-specific values (a workspace
URL, the demo warehouse ID) were replaced with empty/`valueFrom` placeholders
rather than carried forward.

**Licensing (task 1, done):** the user explicitly decided the merged code
should use the more permissive of the two upstream licenses. Elastic
License 2.0 (databricks-cost-observability's license) was judged more
permissive than the Databricks License (lakemeter-oss's) because the latter
restricts use to "in connection with your use of the Databricks Services"
under a separate commercial agreement — a real limitation Elastic 2.0
doesn't have (its main restriction is against re-offering the software as a
competing hosted service). Implemented as `satsyil_lakemeterplus/LICENSE`
(Elastic License 2.0) plus `satsyil_lakemeterplus/NOTICE.md`, which
preserves the upstream attribution and notice-preservation terms both
original licenses require for derivative works (including reproducing
`lakemeter-oss`'s own NOTICE.md dependency table, since that content still
applies). **This is a good-faith technical reading of both license texts,
not legal advice** — if this project is ever distributed beyond
internal/scaffold use, get it reviewed by whoever has authority over each
upstream repository.

**Frontend proof of concept (task 12, partial):** one observability page
shipped — `src/frontend/src/pages/Observability.tsx` (KPI cards from
`/api/v1/observability/cost/summary`, raw-JSON preview of
`/api/v1/observability/executive/summary`), a typed API client
(`src/frontend/src/api/observability.ts`), a `/observability` route in
`App.tsx`, and a nav entry in `Layout.tsx`. Styled to match Lakemeter's
existing CSS-variable-based theme system and heroicons usage. **Not
verified by a build** — no Node.js/npm was available in this environment,
so this was reviewed by hand for syntax/type correctness rather than
compiled with `tsc`/Vite. Treat as higher-risk than the backend changes
until someone runs `npm install && npm run build` on it.

## Not started / explicitly deferred

| # | Task | Why it's not done | Recommended next step |
|---|---|---|---|
| 8 | Merge admin/allowlist model app-wide | Depends on deciding whether `ALLOWED_USERS`/`ADMIN_USERS` (and cost-observability's `AllowlistMiddleware`) should gate Lakemeter's estimation routes too, or stay scoped to `/observability/*` only — a product decision | Get that decision, then wire `AllowlistMiddleware` (or an equivalent) accordingly |
| 12 (remainder) | Frontend pages for the other ~16 observability domains | Largest remaining piece of work by volume | Incremental delivery, one domain per page; reuse Chart.js/D3/3d-force-graph as embedded components rather than rewriting visualizations from scratch |
| 13 | Merge `databricks.yml` (DAB) | Not attempted | Add warehouse/catalog bundle variables + SQL Warehouse permissions as a parallel task in Lakemeter's existing 9-task DAG |
| 15 | De-duplicate alert-sending logic | Not started | `services/alert_service.py` and `scripts/send_cost_alerts.py` were both ported with their pre-existing duplication intact |
| 16 | Migrate `UserPermissionsService` off Delta tables onto Lakebase | Not started (P2, optional) | Only worth it if there's appetite for a schema migration |
| 17 | Reconcile SKU/product-type mapping duplication | Not started | Needs a design decision on whether estimation (cached/synced pricing) and observability (live `system.billing.list_prices`) should share one SKU-naming utility even though they'll keep separate data sources |
| 18 | Unify testing strategy / add unit tests for ported observability services | Not started — **zero test coverage for anything in `src/`** | Highest-value follow-up for correctness confidence beyond the import-time verification done this session |
| 19 | Extend/create CI for the merged app | Blocked on 18; no CI workflow exists for `src/` at all yet | |
| 20 | Cross-link estimate-vs-actual comparison feature | Not started (net-new feature) | Worth a dedicated design doc once both modules are further along |
| 21 | Replace HTML-DOM-manifest smoke checks with component/E2E tests | Blocked on 12 (only one React observability page exists) | |
| 23 | Consolidate documentation sites | Not started (P3) | |
| 24 | Write a deploy workflow for `src/`, avoiding cost-observability's known dev/prod bundle-path bug | Not started — no CI/deploy workflow exists for `src/` yet | |

## Known gaps not captured as numbered merge-tasks

- **No CI/deploy workflow exists yet for `src/`** — neither source repo's
  workflows were copied in.
- **`src/backend/static/`** only contains the `pricing/` CSV bundle and the
  Databricks icon — the compiled React `assets/` bundle isn't checked in
  (build artifact). Running in "combined" mode (single process serving both
  frontend and API) requires `cd src/frontend && npm install && npm run
  build` and copying `dist/` into `src/backend/static/` first.
- **No end-to-end request was made against either module.** Only import-time
  wiring (backend) and hand-review (frontend) were verified this session —
  actually exercising an endpoint needs either a real Databricks workspace +
  Lakebase instance, or local mock/dev fixtures for both modules (Lakemeter
  has none beyond a `DATABASE_URL` override; the observability module's
  `MOCK_MODE` only covers the Unity-Catalog side).
- **No Node.js was available in this environment**, so the frontend changes
  (task 12) could not be built or type-checked — they were written carefully
  against the existing code's conventions and reviewed by hand, but should
  be treated as unverified until someone runs the frontend build.

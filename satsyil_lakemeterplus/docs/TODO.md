# TODO — Remaining Merge Work

Status snapshot of `satsyil_lakemeterplus/src` against the plan in
`merge-tasks.md`. Task numbers below match that file.

## Done this session

| # | Task | What was actually done |
|---|---|---|
| 2 | Scaffold unified `src/` | `src/backend` = copy of `lakemeter-oss` backend app source; `src/frontend` = copy of its React SPA source. Build artifacts (`dist/`, `node_modules/`, compiled `static/assets`) intentionally excluded — regenerate via `npm run build`. |
| 3 | Port observability `core/` | `sql_executor.py`, `validators.py`, `subscriptions.py`, `dependencies.py`, `security.py`, `config.py` copied into `src/backend/app/observability/core/`, imports rewritten to the new package path. |
| 4 | Port observability `services/` | All 18 service files copied into `src/backend/app/observability/services/`, imports rewritten. |
| 5 | Port observability `routes/` + mount | All 20 `api/v1/*.py` routers copied into `src/backend/app/observability/routes/`; `router.py` aggregates them under an `/observability` prefix; `main.py` mounts the aggregate at `/api/v1`, yielding `/api/v1/observability/*` with **zero collisions** against Lakemeter's existing routes. |
| 6 | `WorkspaceClient`/`AccountClient` DI | Came along for free — `observability/core/dependencies.py` was ported verbatim and provides these; not yet cross-wired into Lakemeter's own `auth/token_manager.py` (see task 7, not done). |
| 9 (partial) | Merge `requirements.txt`/`app.yaml` | Dependency lists unioned (`scikit-learn`, `numpy` added). `app.yaml` env vars unioned; **hardcoded environment-specific values found in both source repos** (a specific workspace URL in Lakemeter's `app.yaml`, a demo warehouse ID `21f5bd20b7f44a51` in cost-observability's `app.yaml`) were **removed and replaced with empty/`valueFrom` placeholders** rather than silently carried into the merged file. Settings classes themselves are still **not** unified — see below. |

**Verification performed:** installed both modules' Python dependencies into a scratch virtualenv and actually imported `app.main` (not just `py_compile`). It imports successfully; `app.openapi()` reports 136 total routes, 48 under `/api/v1/observability/*`, with no path collisions against Lakemeter's own routes. This confirms the router wiring is functionally correct, not merely syntactically valid. Full details in `../src/README.md`.

## Not started / explicitly deferred

| # | Task | Why it's not done | Recommended next step |
|---|---|---|---|
| 1 | Resolve Elastic License 2.0 vs. Databricks License conflict | Not an engineering decision — needs sign-off from whoever owns each source repo before the merged code can be distributed | Get an explicit licensing decision before this project goes beyond internal/scaffold use |
| 7 | Unify auth/identity resolution | Two different header-based identity systems (`X-Forwarded-Email` vs. `X-Forwarded-User`/numeric-ID SCIM resolution) need careful reconciliation to avoid silently breaking either app's access control | Write one `resolve_user_identity()` that checks the union of both header sets; keep Lakemeter's DB-backed `get_or_create_user()` as the identity of record; add a regression test asserting both header shapes still resolve correctly |
| 8 | Merge admin/allowlist model | Depends on task 7 | After identity is unified, decide whether `ALLOWED_USERS`/`ADMIN_USERS` env-var checks gate only `/observability/*` or the whole app |
| 9 (remainder) | Unify `Settings`/config classes into one Pydantic settings object | Deferred to keep this pass's blast radius small — the two modules currently read **independent** env-driven settings, which works but means env vars aren't validated/documented in one place | Fold `observability/core/config.py`'s fields into `app/config.py`'s `Settings`, delete the duplicate class, update `observability` imports to use it |
| 10 | Wire `MOCK_MODE` through the merged `sql_executor` | Depends on 9 (config unification) being at least partially done, or can be done standalone since `MOCK_MODE` today lives entirely in the observability module's own settings | Low effort — the rewrite logic ported as-is and already works standalone; just needs an end-to-end smoke test once a real/mock warehouse is available |
| 11 | Port mock/demo data scripts, parameterize hardcoded warehouse ID | Scripts were copied (`observability/scripts/setup_mock_tables.py`, `setup_enterprise_mock_data.py`) but **not yet edited** to remove the hardcoded warehouse ID `21f5bd20b7f44a51` that appears inside the scripts themselves (only the `app.yaml` copy was fixed) | Grep both scripts for the literal ID and replace with an env/config read |
| 12 | Frontend: Observability pages in the React app | Largest remaining piece of work — no React code was written this session, only backend porting | Recommend incremental delivery: start with one page (e.g. Cost Dashboard) calling `/api/v1/observability/cost/summary`, reuse Chart.js as an embedded component rather than rewriting visualizations from scratch, add a nav entry in `frontend/src/components/Layout.tsx` |
| 13 | Merge `databricks.yml` (DAB) | Not attempted — `scripts/databricks.yml` in `src/` is still Lakemeter's original 9-task job DAG; cost-observability's simpler `apps`-resource bundle was not folded in | Add warehouse/catalog bundle variables and a permissions block for the observability module's SQL Warehouse access; likely a new parallel task in the existing DAG rather than a new bundle |
| 15 | De-duplicate alert-sending logic | Not started | `services/alert_service.py` and `scripts/send_cost_alerts.py` (standalone, for scheduled-job use) were both ported as-is with the duplication intact; factor out a shared `detect_spikes()`/email-building module both can import |
| 16 | Migrate `UserPermissionsService` off Delta tables onto Lakebase | Not started (P2 — optional) | Only worth doing if/when task 9 is complete and there's appetite for a schema migration |
| 17 | Reconcile SKU/product-type mapping duplication | Not started | Needs a design decision on whether estimation (cached/synced pricing) and observability (live `system.billing.list_prices`) should share one SKU-naming utility even though they'll keep separate data sources |
| 18 | Unify testing strategy / add unit tests for ported observability services | Not started — **the ported observability module currently has zero test coverage in `src/`**, same as its source repo | Highest-value follow-up for correctness confidence; start with the `harness`-style ordered smoke test pattern Lakemeter already has |
| 19 | Extend CI for the new package | Blocked on 18 | |
| 20 | Cross-link estimate-vs-actual comparison feature | Not started (net-new feature, not just a port) | Worth a dedicated design doc once both modules are independently live |
| 21 | Replace HTML-DOM-manifest smoke checks with component/E2E tests | Blocked on 12 (no React observability pages exist yet) | |
| 22 | Adopt cost-observability's hardened security middleware app-wide | Not started (P3) | `observability/core/security.py` was ported and compiles, but is **not wired into `main.py`** — Lakemeter's app currently has no rate limiting/bot detection/IP banning |
| 23 | Consolidate documentation sites | Not started (P3) | |
| 24 | Fix latent `deploy.yml` prod/dev bundle-path bug | Not started (P3) — this bug lives in `databricks-cost-observability-main/.github/workflows/deploy.yml`, which was not ported into `src/` at all yet (no CI workflow exists for the merged app) | Write a new `src/.github/workflows/deploy.yml` deriving from Lakemeter's simpler single-target deploy, avoiding cost-observability's dev/prod path bug from the start |

## Known gaps not captured as numbered merge-tasks

- **No CI workflow exists yet for `src/`** — neither `lakemeter-oss`'s `ci.yml` nor `databricks-cost-observability`'s `deploy.yml`/`load-enterprise-data.yml` were copied in. Needs a fresh workflow written for the merged layout (task 24 touches this but doesn't cover the full CI story).
- **`src/backend/static/`** only contains the `pricing/` CSV bundle and the Databricks icon — the compiled React `assets/` bundle is intentionally not checked in (build artifact); running the app in "combined" (single-process, serves frontend) mode requires `cd src/frontend && npm install && npm run build` and copying `dist/` into `src/backend/static/` first, same as the source repo's own deploy flow.
- **No end-to-end request was made against either module** — only import-time wiring was verified. Actually exercising an endpoint requires either a real Databricks workspace + Lakebase instance, or building out local mock/dev fixtures for both (Lakemeter has none checked in beyond `DATABASE_URL` override; cost-observability's `MOCK_MODE` covers only the UC side).

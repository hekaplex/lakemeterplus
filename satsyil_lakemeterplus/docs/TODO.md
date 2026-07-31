# TODO — Remaining Merge Work

Status snapshot of `satsyil_lakemeterplus/src` against the plan in
`merge-tasks.md` (which carries a Status column per task — this file is
the narrative version). Of the 24 original tasks: **18 done, 4 partial, 2
not started.** All P0 tasks are done. All P1 tasks are done or partial.
One item exists outside the original 24: a GitLab CI equivalent
(`src/.gitlab-ci.yml`), added alongside the GitHub Actions workflows.

Every "done"/"partial" claim in `merge-tasks.md` was checked by actually
running something — a `pytest` run (currently **115 tests, all passing**),
a live `TestClient` request cycle, a rendered-template YAML parse, a
`bash -n` syntax check, or a real CRUD round-trip against an isolated
database. Where something couldn't be verified (frontend TypeScript/React,
Docusaurus config — no Node.js in this environment), that's called out
explicitly rather than assumed correct.

## What's left — the 2 not-started and 4 partial tasks

| # | Task | Status | Why | Next step |
|---|---|---|---|---|
| 7 | Unify auth/identity resolution into one function | Partial | Header *names* were unioned (closing a real bug), but Lakemeter's DB-backed `get_or_create_user()` and the observability module's stateless `resolve_user_identity()` remain two separate code paths | Would need a decision on which becomes the identity of record |
| 8 | Whether `ALLOWED_USERS`/`ADMIN_USERS` should gate Lakemeter's own routes too | Partial | The observability-only scoping (`ObservabilityAllowlistMiddleware`) is done and tested; extending it app-wide is a **product decision**, not an engineering one | Get the decision, then it's a small code change |
| 12 | Frontend pages for the other ~10 observability domains | Partial | One proof-of-concept page exists (`Observability.tsx`); building the rest is mostly volume, but also the **least-verified work in this whole merge** — no Node.js was available in this environment, so nothing frontend-related (this page, the docs-site TS config edits) has been compiled or type-checked | Get a real `npm run build` run before extending further; that verification gap applies to everything already written, not just what's left |
| 18 | Unit tests for the remaining ~11 observability services | Partial | Time-boxed to the highest-value previously-zero-coverage targets each round (alert math, SQL-injection validators, mock-mode rewrite, `CostService._where()`'s IDOR logic, `ExecutiveService`'s fiscal-year math, the Lakebase-migrated permissions service) | `compute_service.py`, `access_service.py`, and `query_service.py` are the next-largest untested files |
| 20 | Cross-link estimate-vs-actual comparison (net-new feature) | Not started | This was always framed as "worth a dedicated design doc," not a merge requirement — it's a product idea unlocked by the merge, not a gap in it | Needs product scoping, not just engineering |
| 21 | Replace HTML-DOM-manifest smoke checks with component/E2E tests | Not started | Blocked on 12 — nothing to replace them with until more frontend pages exist | |

## Everything else is done — brief pointers, not full detail (see `merge-tasks.md`)

- **Backend wiring** (tasks 2–6, 9, 10): observability module ported, namespaced, mounted at `/api/v1/observability/*`; config unified into one `Settings`; `MOCK_MODE` support preserved. 136 total routes, zero collisions — verified by actually importing the merged app.
- **Deployment** (tasks 13, 14, 24): `databricks.yml`, the `app.yaml` template generator (`scripts/notebooks/05a_create_app.py`), and `scripts/install.sh` all extended for the observability module's config. `deploy.yml` (and its GitLab equivalent) structurally avoid a real bug found in the source repo's own deploy workflow.
- **Security** (task 22): HTTPS redirect, security headers, rate limiting/bot detection wired in app-wide.
- **De-duplication** (tasks 15, 17): alert-sending logic and three separate SKU-mapping implementations (two of them dead code) both consolidated.
- **Lakebase migration** (task 16): `UserPermissionsService` moved off Delta tables onto the same Postgres database as the rest of the app — including finding and fixing a real auth-ordering bug the migration itself introduced.
- **Documentation** (task 23): the Docusaurus site (never actually ported before this) now exists in `src/docs-site/` with a new "Cost Observability" section.
- **Licensing** (task 1): Elastic License 2.0 adopted per explicit user decision — see `../LICENSE`/`../NOTICE.md`. Good-faith reading, not legal advice.

## Known gaps not captured as numbered merge-tasks

- **`install_lakemeter.py`** (the source repo's *other*, overlapping installer implementation) was deliberately not ported — `install.sh` was chosen as authoritative because it's the one actually wired to the merged `databricks.yml`/notebooks, but this was this session's judgment call, not a decision either source repo had already made.
- **`src/backend/static/`** only contains the `pricing/` CSV bundle and the Databricks icon — the compiled React `assets/` bundle isn't checked in. Running in "combined" mode requires `cd src/frontend && npm install && npm run build`, then copying `dist/` into `src/backend/static/`.
- **No end-to-end request against a real Databricks workspace or Lakebase instance was made.** The closest verification: a `TestClient` request that reached real SQL-execution code and failed only for environmental reasons (no `MOCK_MODE`/real warehouse in this sandbox) — meaningfully stronger than import-time checks alone, but still not a real deployment.
- **No Node.js was available in this environment, at any point in this merge.** Every frontend-adjacent change — `Observability.tsx`, `observability.ts`, the docs-site port and its new pages, `sidebars.ts`/`docusaurus.config.ts` edits — was written carefully by hand and checked as thoroughly as possible without a JS toolchain (frontmatter parsing, image-existence checks, bracket-balance checks), but none of it has been compiled or type-checked. Every backend change, by contrast, was verified by actually running Python code.
- **Neither GitHub Actions workflow nor the GitLab CI file has been run through its actual platform** — both were syntax-validated locally (YAML + `bash -n`), which catches structural errors but not e.g. missing repo secrets, permissions issues, or runner-environment differences.

---
sidebar_position: 4
---

# Merge Notes

The cost-observability module wasn't built as part of Lakemeter — it was
merged in from a separate open-source project
(`databricks-cost-observability`) that did the same job for a different
concern: **actual, historical spend** rather than the **hypothetical,
pre-purchase estimates** the rest of this site documents. This page
summarizes what that merge involved, for anyone extending either module.
Full detail (architecture diagrams, a feature-by-feature comparison table,
and a task-by-task status of the merge itself) lives in `docs/` at the
repository root — `architecture-lakemeter-oss.md`,
`architecture-databricks-cost-observability.md`, `feature-comparison.md`,
`merge-tasks.md`, and `TODO.md`.

## What's shared vs. kept separate

**Shared, one implementation each:**
- App configuration (`app/config.py`'s `Settings` class) — the
  observability module's config lives in the same object as the rest of
  Lakemeter's, not a second independent env parse.
- Security middleware (HTTPS redirect, security headers, rate limiting/bot
  detection) — applied app-wide, not just to observability routes.
- Alert email building/sending (`services/alert_email.py`) — used by both
  the API (`/alerts/send-now`) and the standalone scheduled-job script.
- Proxy-header identity recognition — both modules' header lists were
  unioned so a Databricks Apps deployment using either header convention
  works for both modules.
- Per-user tab/workspace/tag permission storage
  (`services/user_permissions_service.py`) — originally its own Delta
  table (`<catalog>.default.app_user_permissions`), migrated onto a
  SQLAlchemy model against the same Lakebase database Lakemeter's
  estimates/line-items live in (`lakemeter.observability_user_permissions`
  — see `app/observability/models.py`). One of only two places the
  observability module touches Lakebase at all — the rest of its data (see
  below) stays on Unity Catalog system tables.
- SKU/product-type-string mapping for estimation. Lakemeter used to carry
  *three* near-identical copies of "workload config → SKU string" logic:
  a Postgres function (`get_product_type_for_pricing`, the one every
  `calculate/*` route actually calls) and two unused Python
  reimplementations of the same branching (`lakebase_queries.get_sku_type`,
  `calculate/helpers.get_sku_type`) — both dead code, confirmed unused
  anywhere in the app or its tests, and removed.

**Deliberately kept separate:**
- **Data access, for everything except user permissions (above).** The
  observability module's dashboards query Unity Catalog `system.*` tables
  via the Databricks SDK's Statement Execution API; Lakemeter's
  estimates/line-items/pricing tables live in Lakebase via SQLAlchemy.
  These stay architecturally separate — unifying them wasn't attempted.
- **Identity resolution.** Header *names* are shared (see above), but
  Lakemeter's database-backed `get_or_create_user()` and the
  observability module's stateless `resolve_user_identity()` are still two
  separate functions.
- **Access control scope.** `ALLOWED_USERS` gates
  `/api/v1/observability/*` only (see
  [Deployment & Configuration](./deployment)). Whether it — or something
  like it — should also gate Lakemeter's own estimation routes is a
  product decision that hasn't been made; extending the scope is a small
  code change once that decision exists.
- **Pricing data sources.** Lakemeter's own cost *estimates* read from
  pricing tables synced ahead of time (stable, cacheable); the
  observability module's cost *dashboards* read live from
  `system.billing.list_prices`. These stay separate on purpose — estimation
  wants stable/cacheable prices, observability wants live actuals — but as
  of the SKU-mapping cleanup above, at least the *duplicate dead code* is
  gone; the two live data sources themselves were never the duplication
  problem.

## Where to look for more

- **Backend code**: `backend/app/observability/` — routes, services, and
  core infra, namespaced as its own Python package.
- **Frontend**: one proof-of-concept page
  (`frontend/src/pages/Observability.tsx`) exists; the other ten dashboards
  above have no React implementation yet.
- **Tests**: `tests/observability/` covers the merge-specific wiring
  (access-control scoping, config sharing, the alert math, SQL-injection
  validators, the mock-mode rewrite) — not the full feature surface of
  either module.

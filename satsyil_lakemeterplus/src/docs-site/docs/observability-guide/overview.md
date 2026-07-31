---
sidebar_position: 1
---

# Overview

The cost-observability module is Lakemeter's second half: where the rest of this
site documents **estimating** what a Databricks workload will cost before you
build it, this module reports what you're **actually spending**, live, once
it's running. It was merged in from a separate open-source project
(`databricks-cost-observability`) rather than built as part of Lakemeter —
see [Merge Notes](./merge-notes) for what that involved and what's still in
progress.

It runs as part of the same Databricks App, mounted at
`/api/v1/observability/*`, and reads directly from Unity Catalog `system.*`
tables via a SQL Warehouse — no data leaves the workspace, and no separate
BI tool or data export is required.

![Cost observability dashboard tabs](/img/observability/tabs.png)
*11 dashboard domains, each reading live from Unity Catalog system tables.*

## What it's for

Four groups get direct value from this module, each covered by a different
set of dashboards:

- **Finance / FinOps** — spend trends, contract-year forecasts, spend
  concentration (Pareto) analysis, savings opportunities.
- **Platform teams** — cluster/warehouse right-sizing, job SLA tracking,
  idle-resource detection.
- **Security / governance** — Unity Catalog permission graphs, row/column
  filter inventory, audit-log analysis.
- **ML/data teams** — model-serving cost and health, AI Gateway token usage,
  data lineage, MLflow experiment/run history.

![Executive scorecard](/img/observability/executive.png)
*The Executive tab: a single cross-domain scorecard combining spend, job
health, user adoption, and governance signals.*

## Works without production system-table access

Many workspaces — trials, sandboxes, lower environments — don't have Unity
Catalog system tables enabled or accessible. `MOCK_MODE` handles that: when
set, every query against `system.*` is rewritten at query time to a
`workspace.mock_system_*` table instead, populated with realistic demo data.
No dashboard code changes, no separate build — the same app, the same
queries, a different data source. See [Deployment & Configuration](./deployment)
for how this is wired into the merged app's installer.

## Next

- [Features by domain](./features) — the full list of what each of the 11
  dashboards covers.
- [Deployment & Configuration](./deployment) — `MOCK_MODE`, the SQL Warehouse
  requirement, and the access-control model.
- [Merge Notes](./merge-notes) — how this module was combined with the rest
  of Lakemeter, and what's still open.

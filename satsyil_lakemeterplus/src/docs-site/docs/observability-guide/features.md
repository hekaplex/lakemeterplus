---
sidebar_position: 2
---

# Features by Domain

Each dashboard below corresponds to one router/service pair in
`backend/app/observability/` (see `routes/` and `services/`), and one tab in
the module's frontend. Screenshots are from the source project; the pages
themselves aren't ported into Lakemeter's React frontend yet beyond a single
proof-of-concept Cost Observability page — see [Merge Notes](./merge-notes).

## Executive & Cost

- 30/60/90-day spend trends with `AI_FORECAST()`-based contract-year
  projection
- Per-workspace, per-SKU, per-user cost attribution
- Spend concentration (Pareto) analysis across workspaces
- Rule-based and ML (Isolation Forest) anomaly detection on running resources
- Configurable spend-spike email alerts (spend trend, single-day extremes,
  new SKUs, fast-growing SKUs)

![Cost dashboard](/img/observability/cost_dashboard.png)

![Anomaly detection](/img/observability/anomalies.png)

## Compute & Jobs

- Cluster and SQL Warehouse right-sizing recommendations based on actual
  node utilization
- Job SLA tracking — success rates, run durations, failure trends
- DLT pipeline cost and update timeline
- SQL Warehouse query attribution and cost-per-query estimation

![Compute sizing](/img/observability/compute_sizing.png)

![Job SLA](/img/observability/job_sla.png)

![Query attribution](/img/observability/query_attribution.png)

## Data & AI

- AI Gateway token usage and cost by model and user
- Model-serving endpoint health, request volume, and latency percentiles
- Data lineage graph (table and column level)
- MLflow experiments, run history, and registered model registry

![AI/LLM usage](/img/observability/ai_llm.png)

![Lineage and ML](/img/observability/lineage_ml.png)

## Governance

- Unity Catalog permission graph — users, groups, service principals,
  catalogs, schemas (rendered as an interactive force-directed graph)
- Row-level security and column mask inventory
- Audit-log analysis and active-user trends

![UC permission graph](/img/observability/uc_graph.png)

![User adoption](/img/observability/user_adoption.png)

## Storage & Platform

- Predictive optimization (`OPTIMIZE`/`ZORDER`/`VACUUM`) operations history
- Table inventory by catalog/schema with type distribution
- Marketplace listing and consumption analytics
- Platform ops — dashboard adoption, network endpoint status

![Storage insights](/img/observability/storage.png)

## Multi-cloud spend (separate from Databricks DBU cost)

A distinct capability from the dashboards above: `Cloud Cost` reads a
separate, app-owned Delta table (`platform.cloud_platform_costs`, populated
by a scheduled ingestion notebook) covering actual Azure/AWS/GCP
infrastructure spend — not Databricks DBU usage. This is a different data
source from Lakemeter's own VM *pricing* tables (used for estimation
inputs), and the two are intentionally not merged into one — see
[Merge Notes](./merge-notes).

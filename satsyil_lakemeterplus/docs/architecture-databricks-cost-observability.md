# Architecture — `databricks-cost-observability-main`

## Summary

A single-process **FastAPI** app deployed as a Databricks App. It serves both a JSON API (`/api/v1/*`) and a monolithic hand-authored `static/index.html` SPA (vanilla JS + Chart.js/D3/3d-force-graph, no build step) from the same process. It has **no database of its own** for the vast majority of features — it queries **Unity Catalog `system.*` tables** live via the Databricks SDK's Statement Execution API (SQL Warehouse REST calls, not JDBC/ODBC). Two exceptions: it owns a small `app_user_permissions` Delta table (per-user tab/workspace restrictions) and a `platform.cloud_platform_costs` Delta table (multi-cloud billing, populated by a separate ingestion notebook). A `MOCK_MODE` flag rewrites all `system.*` table references to `workspace.mock_system_*` so the app can run/demo on any workspace tier without real system-table access.

Auth is entirely delegated to the Databricks Apps reverse proxy: identity comes from forwarded headers (`X-Forwarded-User`, etc.), gated by an `ALLOWED_USERS` email allowlist and an `ADMIN_USERS` admin list — there is no app-level login, JWT, or subscription/license gate.

## Component Diagram

```mermaid
flowchart TB
    subgraph Client["Browser"]
        SPA["static/index.html<br/>vanilla JS + Chart.js + D3 + 3d-force-graph<br/>14 dashboard tabs"]
    end

    subgraph App["FastAPI process (app.py)"]
        MW["Middleware stack:<br/>HTTPSRedirect -> SecurityHeaders -><br/>AuditLog(rate limit/ban) -> Allowlist(auth) -><br/>GZip -> CacheControl -> CORS"]
        Router["api/router.py<br/>20 sub-routers under /api/v1"]
        subgraph Routers["api/v1/*.py (thin routers)"]
            R1["cost.py / ml_cost.py"]
            R2["executive.py"]
            R3["compute.py / cluster_health.py"]
            R4["query.py"]
            R5["ai.py (usage analytics, not chat)"]
            R6["access.py (UC permission graph)"]
            R7["lakeflow.py / storage.py / lineage.py"]
            R8["governance.py / platform_ops.py / marketplace.py"]
            R9["cloud_cost.py"]
            R10["alerts.py"]
            R11["admin.py / user.py / health.py"]
        end
        subgraph Services["services/*.py (business logic + TTL cache)"]
            S1["CostService / MLAnomalyService"]
            S2["ExecutiveService"]
            S3["ComputeService / ClusterHealthService"]
            S4["QueryService"]
            S5["AIService"]
            S6["AccessService"]
            S7["LakeflowService / StorageService / LineageService"]
            S8["GovernanceService / PlatformOpsService / MarketplaceService"]
            S9["CloudCostService"]
            S10["AlertService"]
            S11["UserPermissionsService"]
        end
        Core["core/<br/>sql_executor.py (Statement Execution API + retry + MOCK_MODE rewrite)<br/>validators.py (regex SQL-identifier sanitization)<br/>security.py (rate limit, bans, headers)<br/>dependencies.py (identity resolution, WorkspaceClient DI)<br/>config.py / subscriptions.py"]
    end

    subgraph Databricks["Databricks Workspace / Account"]
        SQLWH["SQL Warehouse<br/>(Statement Execution API)"]
        UC["Unity Catalog system.* tables<br/>billing, access, compute, lakeflow, query,<br/>ai_gateway, serving, mlflow, storage,<br/>information_schema, networking, lakeview, marketplace"]
        DeltaOwn["App-owned Delta tables<br/>catalog.default.app_user_permissions<br/>catalog.platform.cloud_platform_costs"]
        SDK["Databricks SDK<br/>WorkspaceClient / AccountClient<br/>(SCIM users, grants, clusters, jobs...)"]
    end

    subgraph Jobs["Scheduled Databricks Jobs (outside the app)"]
        J1["notebooks/ingest_cloud_costs.ipynb<br/>Azure/AWS/GCP billing APIs -> cloud_platform_costs"]
        J2["scripts/send_cost_alerts.py<br/>duplicate spike-detection + SMTP email"]
        J3["scripts/setup_mock_tables.py /<br/>setup_enterprise_mock_data.py<br/>seeds mock_system_* demo data"]
    end

    SPA -- "fetch() /api/v1/*" --> MW --> Router --> Routers --> Services
    Services --> Core
    Core -- "execute_statement()" --> SQLWH --> UC
    Services -- "MERGE/CRUD" --> DeltaOwn
    Core -- "identity, clusters, jobs, grants" --> SDK --> Databricks
    J1 --> DeltaOwn
    J2 -.->|"reads"| UC
    J3 -.->|"seeds mock_system_*"| UC
```

## Request-lifecycle sequence (typical dashboard tab load)

```mermaid
sequenceDiagram
    participant B as Browser (index.html)
    participant MW as Middleware (Allowlist/Audit/Security)
    participant R as api/v1/<domain>.py router
    participant Svc as services/<domain>_service.py
    participant SE as core/sql_executor.py
    participant WH as Databricks SQL Warehouse
    B->>MW: GET /api/v1/platform/compute-insights
    MW->>MW: resolve identity from X-Forwarded-User
    MW->>MW: check ALLOWED_USERS, rate limit, ban list
    MW->>R: forward request
    R->>Svc: _svc(client).get_compute_insights()
    Svc->>Svc: check in-memory TTL cache
    alt cache miss
        Svc->>SE: execute_sync(sql, warehouse_id)
        SE->>SE: rewrite system.* -> mock_system_* if MOCK_MODE
        SE->>WH: statement_execution.execute_statement()
        WH-->>SE: poll until FINISHED, return rows
        SE-->>Svc: rows
        Svc->>Svc: _analyse() -> aggregate dict, cache it
    end
    Svc-->>R: dict result
    R-->>B: JSON response
    B->>B: Chart.js/D3 render into tab
```

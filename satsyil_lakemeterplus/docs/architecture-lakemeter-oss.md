# Architecture — `lakemeter-oss-main`

## Summary

"Lakemeter" is a Databricks Labs open-source **cost estimation** tool (not observability of actual spend — it prices out *hypothetical* workload configurations before you run them). It's a **FastAPI backend + React/TypeScript/Vite SPA**, with its own **Lakebase (managed Postgres)** database holding application data (users, estimates, line items) and synced pricing/reference data (`sync_*` tables fed by a separate Unity-Catalog-based pricing ETL). The actual DBU/VM cost math is implemented as **PL/pgSQL functions inside Lakebase**, not in Python — the FastAPI routes validate input and call a single orchestrator function (`lakemeter.calculate_line_item_costs`). A built-in **AI Assistant** (Claude via a Databricks-hosted model-serving endpoint, tool-calling) lets users describe workloads in natural language and get proposed line items. Auth uses Databricks Apps forwarded headers + Service-Principal OAuth (via the SDK) for both user identity and for minting short-lived Lakebase database credentials. Deployment is a 9-task Databricks Asset Bundle (DAB) job pipeline invoked by a one-command installer script.

## Component Diagram

```mermaid
flowchart TB
    subgraph Client["Browser"]
        SPA["React 18 + TS + Vite SPA<br/>pages: Estimates, Calculator, EstimateDetail, Pricing, TestCalculations<br/>state: Zustand store (useStore.ts)<br/>components: WorkloadForm, ChatPanel, SkuExplorer, FmapiTokenHelper"]
    end

    subgraph App["FastAPI process (backend/app/main.py)"]
        Auth["auth/<br/>databricks_auth.py (forwarded-header identity)<br/>token_manager.py (SP OAuth -> Lakebase creds)"]
        Routes["routes/<br/>estimates, line_items, workload_types, users,<br/>vm_pricing, export/, reference/, calculate/*, chat.py"]
        Svc["services/<br/>ai_agent.py (EstimateAgent, tool-calling)<br/>ai_client.py (ClaudeAIClient)<br/>lakebase_queries.py (calls PG functions)<br/>validators.py / lakebase_pricing.py / cache.py"]
        ORM["models/ (SQLAlchemy ORM)<br/>User, Estimate, LineItem, Template,<br/>Sharing, ConversationMessage, DecisionRecord,<br/>+ pricing reference models"]
    end

    subgraph Lakebase["Lakebase (managed Postgres) - schema `lakemeter`"]
        AppTables["App tables<br/>users, estimates, line_items, templates,<br/>sharing, conversation_messages, decision_records"]
        SyncTables["sync_* reference/pricing tables<br/>sync_pricing_dbu_rates, sync_pricing_vm_costs,<br/>sync_ref_instance_dbu_rates, sync_ref_dbsql_warehouse_config..."]
        PGFuncs["PL/pgSQL calculator functions<br/>calculate_hours_per_month, get_product_type_for_pricing,<br/>calculate_classic/serverless_compute_dbu, calculate_dbsql_dbu,<br/>calculate_vector_search_dbu, calculate_model_serving_dbu,<br/>calculate_fmapi_*_dbu, calculate_classic/dbsql_vm_costs,<br/>calculate_line_item_costs (top-level orchestrator, 35 params)"]
    end

    subgraph Databricks["Databricks Workspace"]
        ClaudeEP["Model-serving endpoint<br/>databricks-claude-opus-4-6"]
        SDK["Databricks SDK<br/>WorkspaceClient + database.generate_database_credential()"]
        UC["Unity Catalog<br/>lakemeter_catalog.lakemeter.* pricing tables"]
    end

    subgraph ETL["etl/pricing_sync (12+ notebooks, outside the app)"]
        E1["01/08 Fetch DBU Prices"]
        E2["02 Load DBU Rates (Excel)"]
        E3["03/04/05 Fetch AWS/Azure/GCP VM pricing"]
        E4["07 Load DBSQL Rates, 09 Load DBU Multipliers,<br/>10 Serverless Rates, 11/12 FMAPI Rates"]
    end

    SPA -- "axios /api/v1/*" --> Routes
    Routes --> Auth
    Routes --> Svc
    Svc --> ORM --> AppTables
    Svc -- "SELECT * FROM lakemeter.calculate_line_item_costs(...)" --> PGFuncs
    PGFuncs --> SyncTables
    Auth -- "SP OAuth token" --> SDK -- "short-lived PG password" --> Lakebase
    Svc -- "chat.py / ai_agent.py" --> ClaudeEP
    ETL --> UC -- "Lakebase Sync (CDC)" --> SyncTables
```

## AI Assistant sequence (natural-language workload proposal)

```mermaid
sequenceDiagram
    participant B as Browser (ChatPanel.tsx)
    participant R as routes/chat.py
    participant A as services/ai_agent.py (EstimateAgent)
    participant C as services/ai_client.py (ClaudeAIClient)
    participant M as Claude model-serving endpoint
    participant Q as services/lakebase_queries.py
    participant PG as Lakebase PL/pgSQL functions
    B->>R: POST /api/v1/chat/stream {message}
    R->>A: agent.handle_message()
    A->>C: send with TOOLS (propose_workload, ask_clarifying_questions, ...)
    C->>M: OpenAI-compatible chat-completions call
    M-->>C: tool_use: propose_workload(workload_type=JOBS, ...)
    C-->>A: parsed tool call
    A-->>R: SSE event tool_start / tool_result (draft workload, in-memory)
    R-->>B: streamed proposal
    B->>R: POST /chat/{id}/confirm-workload {confirmed:true}
    R->>B: workload config (frontend persists via /line-items API)
    B->>R: POST /api/v1/line-items {...workload config}
    R->>Q: call_calculate_line_item_costs(35 params)
    Q->>PG: SELECT * FROM lakemeter.calculate_line_item_costs(...)
    PG-->>Q: dbu_cost_per_month, vm_cost_per_month, cost_per_month...
    Q-->>R: computed line item
    R-->>B: persisted LineItem with real costs
```

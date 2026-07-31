import api from './client'

// Thin client for the ported cost-observability module, mounted on the
// backend at /api/v1/observability/* (see
// src/backend/app/observability/router.py). Kept in its own file rather
// than folded into client.ts since it is a distinct, still-evolving
// module — see satsyil_lakemeterplus/docs/merge-tasks.md task #12.

// Matches CostService.get_summary() in
// src/backend/app/observability/services/cost_service.py
export interface ObservabilityCostSummary {
  workspace_count?: number | string
  product_count?: number | string
  total_dbus?: number | string
  estimated_cost_usd?: number | string
  [key: string]: unknown
}

export interface ObservabilityExecutiveSummary {
  [key: string]: unknown
}

// Unlike Lakemeter's own endpoints (see client.ts's `unwrap`), the ported
// observability routes return their payload directly with no
// {success, data} envelope — so these calls read response.data as-is.
export const observabilityApi = {
  async getCostSummary(): Promise<ObservabilityCostSummary> {
    const { data } = await api.get<ObservabilityCostSummary>('/observability/cost/summary')
    return data
  },

  async getExecutiveSummary(): Promise<ObservabilityExecutiveSummary> {
    const { data } = await api.get<ObservabilityExecutiveSummary>('/observability/executive/summary')
    return data
  },
}

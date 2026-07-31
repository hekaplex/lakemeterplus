import { useEffect, useState } from 'react'
import { ChartBarIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import {
  observabilityApi,
  type ObservabilityCostSummary,
  type ObservabilityExecutiveSummary,
} from '../api/observability'

// Proof-of-concept page for the ported cost-observability module (see
// satsyil_lakemeterplus/docs/merge-tasks.md task #12). This intentionally
// covers one endpoint (Cost Summary KPIs) with a real UI, and shows the
// Executive Summary payload as raw JSON rather than guessing at a layout
// for its ~14-field response — building the remaining observability tabs
// (Compute, Query Attribution, Access Graph, etc.) is tracked in
// satsyil_lakemeterplus/docs/TODO.md as follow-up work, not attempted here.

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-xl border p-4"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)' }}
    >
      <p className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
        {value}
      </p>
    </div>
  )
}

function formatNumber(value: number | string | undefined): string {
  if (value === undefined || value === null || value === '') return '—'
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function formatCurrency(value: number | string | undefined): string {
  if (value === undefined || value === null || value === '') return '—'
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })
}

export default function Observability() {
  const [costSummary, setCostSummary] = useState<ObservabilityCostSummary | null>(null)
  const [executiveSummary, setExecutiveSummary] = useState<ObservabilityExecutiveSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setError(null)
      try {
        const [cost, executive] = await Promise.all([
          observabilityApi.getCostSummary(),
          observabilityApi.getExecutiveSummary(),
        ])
        if (!cancelled) {
          setCostSummary(cost)
          setExecutiveSummary(executive)
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load observability data'
          setError(message)
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16">
      <div className="flex items-center gap-3 mb-2">
        <ChartBarIcon className="w-6 h-6" style={{ color: 'var(--databricks-red)' }} />
        <h1 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>
          Cost Observability
        </h1>
      </div>
      <p className="mb-6 text-sm" style={{ color: 'var(--text-muted)' }}>
        Live spend and platform telemetry from Unity Catalog system tables — distinct from the
        cost estimates elsewhere in this app, which model hypothetical workloads before you run them.
      </p>

      {error && (
        <div
          className="mb-6 flex items-start gap-3 rounded-xl border p-4 text-sm"
          style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)', color: 'var(--text-secondary)' }}
        >
          <ExclamationTriangleIcon className="w-5 h-5 flex-shrink-0 text-amber-500" />
          <div>
            <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
              Couldn't load observability data
            </p>
            <p className="mt-1">{error}</p>
            <p className="mt-1" style={{ color: 'var(--text-muted)' }}>
              This module queries Unity Catalog system tables via a SQL Warehouse — it needs
              DATABRICKS_WAREHOUSE_ID configured (and MOCK_MODE=true for demo data) to respond.
            </p>
          </div>
        </div>
      )}

      {isLoading && !error && (
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Loading...
        </p>
      )}

      {!isLoading && !error && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <KpiCard label="Estimated Cost" value={formatCurrency(costSummary?.estimated_cost_usd)} />
            <KpiCard label="Total DBUs" value={formatNumber(costSummary?.total_dbus)} />
            <KpiCard label="Workspaces" value={formatNumber(costSummary?.workspace_count)} />
            <KpiCard label="Products" value={formatNumber(costSummary?.product_count)} />
          </div>

          <div
            className="rounded-xl border p-4"
            style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-primary)' }}
          >
            <p className="text-xs uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
              Executive Summary (raw)
            </p>
            <pre
              className="text-xs overflow-x-auto whitespace-pre-wrap"
              style={{ color: 'var(--text-secondary)' }}
            >
              {JSON.stringify(executiveSummary, null, 2)}
            </pre>
          </div>
        </>
      )}
    </div>
  )
}

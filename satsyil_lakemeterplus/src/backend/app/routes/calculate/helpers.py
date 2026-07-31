"""Shared helper functions for calculation endpoints."""

# Note: this module used to also define a get_sku_type() here — a third,
# unused-by-any-caller reimplementation of the same workload-config -> SKU
# mapping as app.services.lakebase_queries.get_product_type_for_pricing()
# (the one every calculate/* route actually calls). Confirmed unused
# anywhere in the app or its tests and removed; see
# docs/merge-tasks.md task #17.


def build_sku_breakdown_classic(
    sku_type: str,
    dbu_cost: float,
    dbu_quantity: float,
    dbu_price: float,
    driver_vm_cost: float,
    worker_vm_cost: float,
    hours_per_month: float,
    driver_vm_price_per_hour: float,
    worker_vm_price_per_hour: float,
    driver_pricing_tier: str,
    worker_pricing_tier: str,
    num_workers: int,
):
    """Build flat-list SKU breakdown for classic compute workloads."""
    breakdown = []

    if dbu_cost > 0:
        breakdown.append({
            "type": "dbu",
            "sku": sku_type,
            "cost": round(dbu_cost, 2),
            "qty": round(dbu_quantity, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(dbu_price, 6),
        })

    if driver_vm_cost > 0:
        breakdown.append({
            "type": "vm",
            "sku": f"VM_{driver_pricing_tier.upper()}",
            "cost": round(driver_vm_cost, 2),
            "qty": round(hours_per_month, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(driver_vm_price_per_hour, 6),
        })

    if worker_vm_cost > 0 and num_workers > 0:
        breakdown.append({
            "type": "vm",
            "sku": f"VM_{worker_pricing_tier.upper()}",
            "cost": round(worker_vm_cost, 2),
            "qty": round(hours_per_month * num_workers, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(worker_vm_price_per_hour, 6),
        })

    return breakdown


def build_sku_breakdown_serverless(
    sku_type: str,
    dbu_cost: float,
    dbu_quantity: float,
    dbu_price: float,
):
    """Build flat-list SKU breakdown for serverless workloads (DBU only)."""
    breakdown = []
    if dbu_cost > 0:
        breakdown.append({
            "type": "dbu",
            "sku": sku_type,
            "cost": round(dbu_cost, 2),
            "qty": round(dbu_quantity, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(dbu_price, 6),
        })
    return breakdown

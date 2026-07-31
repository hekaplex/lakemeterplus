from fastapi import APIRouter
from app.observability.routes import cost, health, user, admin
from app.observability.routes import ml_cost
from app.observability.routes import audit, compute, query, ai, access
from app.observability.routes import lakeflow, storage, lineage
from app.observability.routes import governance, cluster_health, marketplace, platform_ops
from app.observability.routes import executive
from app.observability.routes import alerts
from app.observability.routes import cloud_cost

api_router = APIRouter()
api_router.include_router(user.router,          prefix="/observability")
api_router.include_router(admin.router,         prefix="/observability")
api_router.include_router(executive.router,     prefix="/observability")
api_router.include_router(health.router,        prefix="/observability")
api_router.include_router(cost.router,          prefix="/observability")
api_router.include_router(ml_cost.router,       prefix="/observability")
api_router.include_router(audit.router,         prefix="/observability")
api_router.include_router(compute.router,       prefix="/observability")
api_router.include_router(query.router,         prefix="/observability")
api_router.include_router(ai.router,            prefix="/observability")
api_router.include_router(access.router,        prefix="/observability")
api_router.include_router(lakeflow.router,      prefix="/observability")
api_router.include_router(storage.router,       prefix="/observability")
api_router.include_router(lineage.router,       prefix="/observability")
api_router.include_router(governance.router,    prefix="/observability")
api_router.include_router(cluster_health.router, prefix="/observability")
api_router.include_router(marketplace.router,   prefix="/observability")
api_router.include_router(platform_ops.router,  prefix="/observability")
api_router.include_router(alerts.router,        prefix="/observability")
api_router.include_router(cloud_cost.router,    prefix="/observability")

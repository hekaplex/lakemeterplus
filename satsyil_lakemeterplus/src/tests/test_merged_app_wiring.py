"""Regression tests for the merge wiring itself (docs/merge-tasks.md tasks
#5, #9, #22): the observability module's routes are mounted without
colliding with Lakemeter's own routes, the security middleware stack is in
the expected order, and the two modules' config classes are genuinely the
same instance rather than two independent env parses.

These codify checks that were originally done by hand (see ../README.md
"Verified so far") as an actual automated test, so future changes to
main.py can't silently regress them.
"""


def test_no_route_collisions_between_modules(app):
    schema = app.openapi()
    paths = set(schema["paths"].keys())

    observability_paths = {p for p in paths if "/observability" in p}
    lakemeter_paths = paths - observability_paths

    # Sanity: both modules actually contributed routes.
    assert len(observability_paths) > 0, "expected observability routes to be mounted"
    assert len(lakemeter_paths) > 5, "expected Lakemeter's own routes to still be present"

    # The whole point of namespacing under /observability was to guarantee
    # no overlap with Lakemeter's own /api/v1/* routes.
    assert observability_paths.isdisjoint(lakemeter_paths)


def test_observability_routes_use_expected_prefix(app):
    schema = app.openapi()
    paths = schema["paths"].keys()
    observability_paths = [p for p in paths if "/observability" in p]
    assert all(p.startswith("/api/v1/observability/") for p in observability_paths)

    # Spot-check a handful of specific endpoints from key domains exist
    # under the expected prefix (see app/observability/router.py).
    for expected in (
        "/api/v1/observability/cost/summary",
        "/api/v1/observability/executive/summary",
        "/api/v1/observability/admin/users",
        "/api/v1/observability/alerts/summary",
        "/api/v1/observability/health/",
    ):
        assert expected in paths, f"expected {expected} to be registered"


def test_lakemeter_routes_unaffected_by_merge(app):
    schema = app.openapi()
    paths = schema["paths"].keys()
    for expected in (
        "/api/v1/estimates",
        "/api/v1/line-items/",
        "/api/v1/chat",
        "/api/v1/chat/stream",
    ):
        assert expected in paths, f"expected pre-existing Lakemeter route {expected} to still be registered"


def test_security_middleware_stack_order(app):
    names = [m.cls.__name__ for m in app.user_middleware]
    # Outermost-first order established in main.py: HTTPS redirect and
    # security headers wrap everything; the observability allowlist sits
    # between the audit logger and CORS so it only ever sees requests that
    # already passed rate limiting.
    assert names == [
        "HTTPSRedirectMiddleware",
        "SecurityHeadersMiddleware",
        "AuditLogMiddleware",
        "ObservabilityAllowlistMiddleware",
        "CORSMiddleware",
    ]


def test_observability_config_is_shared_with_app_config():
    """docs/merge-tasks.md task #9: app/observability/core/config.py must be
    a shim over app.config.settings, not a second independent Settings
    instance — otherwise env vars would need to be parsed/kept in sync twice.
    """
    from app.config import settings
    from app.observability.core.config import get_settings as obs_get_settings

    assert obs_get_settings() is settings

"""Access-control middleware for the observability module, ported from
databricks-cost-observability's app.py (AllowlistMiddleware + _forbidden_html
lived directly in that app's entrypoint, not in core/, since the original
app had no other module to scope them to).

Scoped deliberately: this only enforces ALLOWED_USERS on
`/api/v1/observability/*` paths. Applying cost-observability's original
allowlist app-wide would change access control for Lakemeter's own
estimation routes too — that's a product decision for whoever owns this
project, not a mechanical port (see satsyil_lakemeterplus/docs/TODO.md
task #8). Restricting the scope here means the observability module gets
real access control without that decision being made implicitly.
"""
import html as _html
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse

from app.observability.core.config import get_settings
from app.observability.core.dependencies import resolve_user_identity

_log = logging.getLogger("security")

# Everything under this prefix is in scope for the allowlist check.
_SCOPE_PREFIX = "/api/v1/observability/"

# Paths that bypass the check even within scope (health check).
_PUBLIC_PATHS = {
    "/api/v1/observability/health",
    "/api/v1/observability/health/",
}


def _forbidden_html(user: str = "") -> str:
    user_line = (
        f'<p style="margin-top:12px;font-size:0.8rem;color:#4b5563">'
        f'Signed in as <code style="color:#9ca3af">{_html.escape(user)}</code></p>'
    ) if user else ""
    return f"""<!doctype html>
<html><head><title>Access Denied</title>
<style>body{{font-family:sans-serif;background:#0f1117;color:#e5e7eb;
  display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
  .box{{text-align:center}}.icon{{font-size:3rem;margin-bottom:12px}}
  h1{{color:#f87171;margin:0 0 8px}}p{{color:#6b7280;font-size:0.9rem}}
</style>
</head><body><div class="box">
  <div class="icon">&#128274;</div>
  <h1>Access Denied</h1>
  <p>You are not authorised to use this application.<br>
     Contact the workspace administrator to request access.</p>
  {user_line}
</div></body></html>"""


class ObservabilityAllowlistMiddleware(BaseHTTPMiddleware):
    """Restrict access to `/api/v1/observability/*` to users listed in
    ALLOWED_USERS (or any workspace-authenticated user if ALLOWED_USERS is
    empty). Requests outside that path prefix pass through untouched.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(_SCOPE_PREFIX):
            return await call_next(request)
        if path in _PUBLIC_PATHS:
            return await call_next(request)

        settings = get_settings()
        user = resolve_user_identity(request)
        ip = request.headers.get(
            "x-forwarded-for",
            request.client.host if request.client else "unknown",
        ).split(",")[0].strip()

        is_dev_localhost = (
            settings.environment == "development"
            and request.client
            and request.client.host in ["127.0.0.1", "localhost"]
        )
        if is_dev_localhost and not user:
            user = "local-dev@localhost"
            _log.debug("DEVELOPMENT_MODE allowing localhost request without auth")

        if not user:
            _log.warning(
                "OBSERVABILITY_AUTH_NO_IDENTITY ip=%s path=%s method=%s",
                ip, path, request.method,
            )
            return HTMLResponse(_forbidden_html(), status_code=403)

        if not is_dev_localhost:
            allowed = settings.allowed_users_set
            if allowed and user not in allowed:
                _log.warning(
                    "OBSERVABILITY_AUTH_NOT_ALLOWED user=%s ip=%s path=%s",
                    user, ip, path,
                )
                return HTMLResponse(_forbidden_html(user), status_code=403)

        return await call_next(request)

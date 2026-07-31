"""Application configuration settings."""
import os
import logging
from urllib.parse import quote_plus
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment: "local", "development", "production"
    environment: str = "local"
    
    # Log level: DEBUG, INFO, WARNING, ERROR
    log_level: str = "INFO"
    
    # Lakebase Database Configuration
    db_host: str = ""
    db_user: str = ""
    db_name: str = "lakemeter_pricing"
    db_port: int = 5432
    db_sslmode: str = "require"
    
    # Databricks configuration
    # In Databricks Apps: DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET
    # are auto-injected. The app's built-in SP handles all authentication.
    databricks_host: Optional[str] = None
    databricks_config_profile: Optional[str] = None
    
    # Lakebase instance name (from Compute > Lakebase Postgres)
    lakebase_instance_name: Optional[str] = None
    
    # Override with full DATABASE_URL if provided
    database_url: Optional[str] = None
    
    # JWT Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:5175"

    # =========================================================================
    # Cost-observability module settings
    # (ported from databricks-cost-observability's core/config.py; folded in
    # here so the whole app has one Settings source. See
    # satsyil_lakemeterplus/docs/merge-tasks.md task #9.)
    # =========================================================================

    # Additional Databricks Apps auto-injected fields the observability
    # module reads directly (Lakemeter only used databricks_host/config_profile above)
    databricks_client_id: str = ""
    databricks_client_secret: str = ""
    databricks_token: str = ""
    databricks_app_port: int = 8000
    databricks_app_name: str = "local"
    databricks_workspace_id: str = ""
    databricks_account_id: str = ""

    # Bound via app.yaml — the SQL Warehouse and Unity Catalog the
    # observability module queries `system.*` tables through.
    databricks_warehouse_id: str = ""
    uc_catalog_name: str = "workspace"

    app_version: str = "1.1.0"

    # Access control — comma-separated list of allowed email addresses.
    # Enforced via the X-Forwarded-User header injected by Databricks Apps.
    # Leave empty to allow all authenticated workspace users.
    allowed_users: str = ""

    # Workspace scoping — comma-separated list of workspace IDs users may query.
    # When empty, billing queries are scoped to the current workspace only.
    # Set to "*" to allow querying across all workspaces (admin mode).
    allowed_workspace_ids: str = ""

    # ── Cloud Platform Cost credentials ───────────────────────────────────────
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_subscription_ids: str = ""   # comma-separated GUIDs

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_account_ids: str = ""          # comma-separated account IDs

    gcp_service_account_json: str = ""  # full JSON as a single-line string
    gcp_project_ids: str = ""           # comma-separated project IDs
    gcp_billing_account_id: str = ""    # e.g. "012345-ABCDEF-012345"

    # Per-user tab and workspace restrictions — JSON string mapping email → config.
    user_configs: str = ""

    # Comma-separated emails with Admin-panel / permission-management access.
    admin_users: str = ""

    # JSON mapping of Databricks numeric user IDs to email addresses.
    user_id_map: str = ""

    @property
    def allowed_users_set(self) -> set:
        return {e.strip().lower() for e in self.allowed_users.split(",") if e.strip()}

    @property
    def allowed_workspace_ids_set(self) -> set:
        """Workspace IDs the app may query. Empty = current workspace only. {"*"} = unrestricted."""
        return {w.strip() for w in self.allowed_workspace_ids.split(",") if w.strip()}

    @property
    def admin_users_set(self) -> set:
        return {e.strip().lower() for e in self.admin_users.split(",") if e.strip()}

    @property
    def user_configs_dict(self) -> dict:
        import json
        if not self.user_configs.strip():
            return {}
        try:
            return json.loads(self.user_configs)
        except (ValueError, TypeError):
            return {}

    @property
    def user_id_map_dict(self) -> dict:
        import json
        if not self.user_id_map.strip():
            return {}
        try:
            return {k.lower().strip(): v.lower().strip() for k, v in json.loads(self.user_id_map).items()}
        except (ValueError, TypeError):
            return {}

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list. Empty string means same-origin only."""
        if not self.cors_origins or self.cors_origins.strip() == "":
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @property
    def use_oauth(self) -> bool:
        """Check if OAuth authentication is configured (Databricks Apps auto-injects host)."""
        return bool(self.databricks_host)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_local(self) -> bool:
        """Check if running in local development."""
        return self.environment.lower() == "local"
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging():
    """Configure logging based on environment."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    if settings.is_production:
        # Production: minimal logging, only warnings and errors
        logging.basicConfig(
            level=logging.WARNING,
            format=log_format
        )
    else:
        # Local/Development: verbose logging
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format=log_format
        )
    
    # Suppress noisy third-party loggers in production
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with environment-aware settings."""
    return logging.getLogger(name)


# Helper for conditional logging (backwards compatible with print statements)
def log_debug(message: str, logger_name: str = "lakemeter"):
    """Log debug message (only in local/dev)."""
    if not settings.is_production:
        get_logger(logger_name).debug(message)


def log_info(message: str, logger_name: str = "lakemeter"):
    """Log info message (only in local/dev)."""
    if not settings.is_production:
        get_logger(logger_name).info(message)


def log_warning(message: str, logger_name: str = "lakemeter"):
    """Log warning message (always)."""
    get_logger(logger_name).warning(message)


def log_error(message: str, logger_name: str = "lakemeter"):
    """Log error message (always)."""
    get_logger(logger_name).error(message)

"""SQLAlchemy models for the observability module.

Currently just the per-user tab/workspace/tag permission store — see
services/user_permissions_service.py, migrated from Delta-table storage
onto Lakebase (the same Postgres database the rest of the app uses) per
docs/merge-tasks.md task #16. The table itself is created by
scripts/notebooks/02_create_database.py alongside Lakemeter's own tables.
"""
from sqlalchemy import Column, String, Text, DateTime

from app.database import Base


class ObservabilityUserPermission(Base):
    """Per-user tab/workspace/tag access restrictions for the observability
    module's dashboards. `config` holds a JSON blob (tabs/workspaces/tags/
    notes) rather than individual columns, matching the original Delta
    table's schema-free design so new filter types don't need a migration.
    """

    __tablename__ = "observability_user_permissions"
    __table_args__ = {"schema": "lakemeter"}

    email = Column(String(255), primary_key=True)
    config = Column(Text, nullable=False)
    updated_at = Column(DateTime)
    updated_by = Column(String(255))

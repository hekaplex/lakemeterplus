"""Lakebase-backed per-user tab/workspace/tag permission store.

Migrated from Delta-table storage (a MERGE-based Databricks SQL Statement
Execution API pattern, reading/writing `<catalog>.default.app_user_permissions`)
onto a SQLAlchemy model against Lakebase — the same Postgres database the
rest of the app uses — per docs/merge-tasks.md task #16. See
app/observability/models.py for the table definition and
scripts/notebooks/02_create_database.py for where it's actually created at
install time.

Public method signatures (get_all/get_for_user/upsert/delete) are
unchanged from the Delta-backed version, so callers only needed to start
passing a `Session` in — see routes/user.py and routes/admin.py.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.observability.models import ObservabilityUserPermission

_log = logging.getLogger("user_permissions")


class UserPermissionsService:
    def __init__(self, db: Session):
        self._db = db

    def get_all(self) -> list[dict]:
        rows = (
            self._db.query(ObservabilityUserPermission)
            .order_by(ObservabilityUserPermission.email)
            .all()
        )
        result = []
        for r in rows:
            try:
                cfg = json.loads(r.config or "{}")
            except (ValueError, TypeError):
                cfg = {}
            result.append({
                "email": r.email,
                "config": cfg,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "updated_by": r.updated_by,
            })
        return result

    def get_for_user(self, email: str) -> Optional[dict]:
        row = self._get_row(email)
        if row is None:
            return None
        try:
            return json.loads(row.config or "{}")
        except (ValueError, TypeError):
            return None

    def upsert(self, email: str, config: dict, updated_by: str) -> None:
        email_norm = email.strip().lower()
        config_json = json.dumps(config, ensure_ascii=False)
        now = datetime.utcnow()

        row = self._get_row(email_norm)
        if row is not None:
            row.config = config_json
            row.updated_at = now
            row.updated_by = updated_by
        else:
            self._db.add(ObservabilityUserPermission(
                email=email_norm, config=config_json,
                updated_at=now, updated_by=updated_by,
            ))
        self._db.commit()

    def delete(self, email: str) -> None:
        email_norm = email.strip().lower()
        self._db.query(ObservabilityUserPermission).filter(
            ObservabilityUserPermission.email == email_norm
        ).delete()
        self._db.commit()

    def _get_row(self, email: str) -> Optional[ObservabilityUserPermission]:
        return (
            self._db.query(ObservabilityUserPermission)
            .filter(ObservabilityUserPermission.email == email.strip().lower())
            .first()
        )


def get_service(db: Session) -> UserPermissionsService:
    """Construct a UserPermissionsService bound to the given DB session.

    Unlike the old Delta-backed version, this is no longer a lazily-created
    module-level singleton — SQLAlchemy Sessions are request-scoped (see
    app.database.get_db), so callers obtain one per request via FastAPI's
    `Depends(get_db)` and pass it straight through.
    """
    return UserPermissionsService(db)

"""Unit tests for UserPermissionsService
(app/observability/services/user_permissions_service.py) — migrated from
Delta-table storage onto Lakebase (SQLAlchemy against Postgres) in
docs/merge-tasks.md task #16. This exercises the migration against a real
database round-trip, not a mock: an isolated in-memory SQLite engine, kept
separate from app.database (which is Postgres-only — its connection pool
kwargs, e.g. max_overflow/pool_timeout, aren't valid for SQLite, see
conftest.py's DATABASE_URL note) so the service's actual SQL/ORM behavior
gets verified rather than just its Python control flow.

SQLite doesn't support Postgres-style schemas the way `ObservabilityUserPermission`
declares (__table_args__ = {"schema": "lakemeter"}) — `ATTACH DATABASE
':memory:' AS lakemeter` on connect, combined with StaticPool so the
attached in-memory database persists across connections in the pool, makes
SQLite accept it. This was verified empirically before being written here
as a fixture, not assumed to work.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.observability.models import ObservabilityUserPermission
from app.observability.services.user_permissions_service import get_service


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _attach_schema(dbapi_conn, _):
        dbapi_conn.execute('ATTACH DATABASE ":memory:" AS lakemeter')

    Base.metadata.create_all(bind=engine, tables=[ObservabilityUserPermission.__table__])

    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def service(db_session):
    return get_service(db_session)


class TestGetForUser:
    def test_returns_none_when_no_row_exists(self, service):
        assert service.get_for_user("nobody@example.com") is None

    def test_returns_config_after_upsert(self, service):
        service.upsert("alice@example.com", {"tabs": ["cost"]}, "admin@example.com")
        assert service.get_for_user("alice@example.com") == {"tabs": ["cost"]}

    def test_lookup_is_case_insensitive(self, service):
        service.upsert("Alice@Example.com", {"tabs": ["cost"]}, "admin@example.com")
        assert service.get_for_user("ALICE@EXAMPLE.COM") == {"tabs": ["cost"]}


class TestUpsert:
    def test_stores_email_lowercased(self, service):
        service.upsert("Bob@Example.COM", {"tabs": []}, "admin@example.com")
        rows = service.get_all()
        assert rows[0]["email"] == "bob@example.com"

    def test_updates_existing_row_rather_than_duplicating(self, service):
        service.upsert("alice@example.com", {"tabs": ["cost"]}, "admin@example.com")
        service.upsert("alice@example.com", {"tabs": ["cost", "executive"]}, "admin2@example.com")

        rows = service.get_all()
        assert len(rows) == 1
        assert rows[0]["config"] == {"tabs": ["cost", "executive"]}
        assert rows[0]["updated_by"] == "admin2@example.com"

    def test_sets_updated_at(self, service):
        service.upsert("alice@example.com", {"tabs": []}, "admin@example.com")
        rows = service.get_all()
        assert rows[0]["updated_at"] is not None


class TestGetAll:
    def test_empty_store_returns_empty_list(self, service):
        assert service.get_all() == []

    def test_returns_rows_ordered_by_email(self, service):
        service.upsert("zoe@example.com", {}, "admin@example.com")
        service.upsert("alice@example.com", {}, "admin@example.com")
        service.upsert("mike@example.com", {}, "admin@example.com")

        emails = [r["email"] for r in service.get_all()]
        assert emails == sorted(emails)

    def test_malformed_config_json_degrades_to_empty_dict(self, service, db_session):
        # Write a row with invalid JSON directly (bypassing upsert's
        # json.dumps) to simulate corrupted/pre-migration data.
        db_session.add(ObservabilityUserPermission(
            email="broken@example.com", config="{not valid json",
            updated_at=None, updated_by="admin@example.com",
        ))
        db_session.commit()

        rows = service.get_all()
        assert rows[0]["config"] == {}


class TestDelete:
    def test_removes_the_row(self, service):
        service.upsert("alice@example.com", {"tabs": ["cost"]}, "admin@example.com")
        service.delete("alice@example.com")
        assert service.get_for_user("alice@example.com") is None

    def test_delete_is_case_insensitive(self, service):
        service.upsert("Alice@Example.com", {"tabs": ["cost"]}, "admin@example.com")
        service.delete("ALICE@EXAMPLE.COM")
        assert service.get_all() == []

    def test_deleting_nonexistent_user_does_not_raise(self, service):
        service.delete("nobody@example.com")  # should be a no-op, not an error
        assert service.get_all() == []

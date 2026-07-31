"""Shared pytest fixtures for satsyil_lakemeterplus.

This test suite covers the merge work done in this repo (see
../docs/merge-tasks.md and ../docs/TODO.md) — it is not a port of either
source repo's own test suite. Lakemeter's extensive tests/ directory and
cost-observability's tests/smoke_test.py were both left in their original
repos; this suite specifically exercises the *new* wiring: the merged
app's routing, the observability module's access control, the unified
config, and the de-duplicated alert logic.
"""
import os

import pytest

# Set before any `app.*` import so pydantic-settings picks these up.
# sqlite is intentionally invalid for Lakemeter's Postgres-only connection
# pool args (see app/database.py) — that's fine, database init fails
# non-fatally at import time and Lakemeter's own DB-backed routes aren't
# under test here.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("ALLOWED_USERS", "")
os.environ.setdefault("ADMIN_USERS", "")
os.environ.setdefault("MOCK_MODE", "false")


@pytest.fixture(scope="session")
def app():
    import app.main
    return app.main.app


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def user_headers():
    return {"X-Forwarded-User": "alice@example.com"}

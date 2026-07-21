"""Shared pytest fixtures."""

import os
import sys
from pathlib import Path

# Configure test DB before app imports create settings/engine.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("AUTH_ENABLED", "false")

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.main import app
from db import session as db_session
from db.session import Base, get_db

get_settings.cache_clear()
db_session._engine = None
db_session._SessionLocal = None


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    from db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

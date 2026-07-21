"""SQLAlchemy engine and session factory (SQLite now, Postgres later)."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def _normalize_database_url(url: str) -> str:
    """Resolve relative SQLite paths against the backend package root."""
    if not url.startswith("sqlite:///"):
        return url
    raw_path = url.removeprefix("sqlite:///")
    if raw_path in {":memory:", ""}:
        return url
    path = Path(raw_path)
    if not path.is_absolute():
        backend_root = Path(__file__).resolve().parents[1]
        path = (backend_root / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return url


def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy engine (lazy)."""
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        url = _normalize_database_url(settings.database_url)
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, future=True)

        if url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        _SessionLocal = sessionmaker(
            bind=_engine, autoflush=False, autocommit=False, future=True
        )
    return _engine


def get_session_factory() -> sessionmaker:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    from db import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())

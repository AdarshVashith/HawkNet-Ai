"""Hash-chained AI audit log tests (legal admissibility)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services import audit_log as audit_service  # noqa: E402
from db.models import AiAuditLog  # noqa: E402
from db.session import Base  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _insert_sample_events(db, count: int = 5) -> list[AiAuditLog]:
    rows: list[AiAuditLog] = []
    modules = [
        "scam_detection",
        "counterfeit",
        "fraud_graph",
        "geospatial",
        "citizen_shield",
    ]
    for i in range(count):
        row = audit_service.record_ai_decision(
            db,
            module_name=modules[i % len(modules)],
            input_payload={"sample_index": i, "text": f"payload-{i}"},
            model_version="stub-0.1.0",
            confidence_score=0.1 * (i + 1),
            decision_output={"label": "sample", "index": i, "risk": "low" if i < 3 else "high"},
        )
        rows.append(row)
    return rows


def test_record_five_events_and_chain_is_valid(db_session):
    rows = _insert_sample_events(db_session, 5)
    assert len(rows) == 5

    # First event links to genesis
    assert rows[0].previous_hash == audit_service.GENESIS_HASH
    # Each subsequent event links to previous entry_hash
    for prev, curr in zip(rows, rows[1:]):
        assert curr.previous_hash == prev.entry_hash

    report = audit_service.verify_chain(db_session)
    assert report["valid"] is True
    assert report["checked_count"] == 5
    assert report["broken_at_event_id"] is None

    # input_reference is a SHA-256 hex digest, not raw input
    assert all(len(r.input_reference) == 64 for r in rows)
    assert all("payload-" not in r.input_reference for r in rows)


def test_chain_verification_fails_when_row_tampered(db_session):
    rows = _insert_sample_events(db_session, 5)
    assert audit_service.verify_chain(db_session)["valid"] is True

    # Tamper with the middle event's decision_output without updating entry_hash
    victim = rows[2]
    victim.decision_output = '{"label":"TAMPERED","index":2}'
    db_session.add(victim)
    db_session.commit()

    report = audit_service.verify_chain(db_session)
    assert report["valid"] is False
    assert report["broken_at_event_id"] == victim.event_id
    assert "tampered" in report["message"].lower() or "mismatch" in report["message"].lower()

    # Verification up to an earlier (untampered) event still succeeds
    early = audit_service.verify_chain(db_session, up_to_event_id=rows[1].event_id)
    assert early["valid"] is True
    assert early["checked_count"] == 2


def test_chain_verification_fails_when_link_broken(db_session):
    rows = _insert_sample_events(db_session, 5)
    victim = rows[3]
    victim.previous_hash = "f" * 64  # break link to predecessor
    db_session.add(victim)
    db_session.commit()

    report = audit_service.verify_chain(db_session)
    assert report["valid"] is False
    assert report["broken_at_event_id"] == victim.event_id


def test_get_audit_event_api_returns_record_and_chain(client):
    # Insert via service using the same DB override as the API client fixture
    from app.main import app
    from db.session import get_db

    # Pull the overridden session from the FastAPI dependency
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        rows = _insert_sample_events(db, 5)
        target = rows[-1]
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    response = client.get(f"/api/audit/{target.event_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["record"]["event_id"] == target.event_id
    assert body["record"]["module_name"]
    assert len(body["record"]["input_reference"]) == 64
    assert body["chain_verification"]["valid"] is True
    assert body["chain_verification"]["checked_count"] == 5

    missing = client.get("/api/audit/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404

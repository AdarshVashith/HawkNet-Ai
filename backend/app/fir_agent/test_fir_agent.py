"""
Tests for the FIR drafting agent. Run with:
    cd backend && PYTHONPATH=. pytest app/fir_agent/test_fir_agent.py -v

These tests avoid a live Anthropic API call (no key needed) by mocking the
network call and using a real in-memory SQLite DB seeded with test data.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

# Use the real ORM models and session infrastructure
from db.models import AiAuditLog
from db.session import Base
from app.fir_agent.schema import (
    ComplainantInfo,
    DraftStatus,
    EvidenceItem,
    FIRDraftRequest,
    SourceModule,
)
from app.fir_agent.legal_reference import lookup
from app.fir_agent import api
from app.fir_agent.grounding_check import check_grounding, extract_claims


# ─── Test DB fixture ──────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    """In-memory SQLite session seeded with a few AiAuditLog rows."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @sa_event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    # Seed two audit log rows for testing
    session.add(AiAuditLog(
        event_id="evt-1",
        timestamp="2026-07-01T10:00:00Z",
        module_name="scam_detection",
        input_reference="hash_evt1",
        model_version="v1.0",
        confidence_score=0.95,
        decision_output=json.dumps({"risk_level": "high", "risk_score": 0.95}),
        human_reviewer=None,
        review_action="confirm",
        previous_hash="0" * 64,
        entry_hash="a" * 64,
    ))
    session.add(AiAuditLog(
        event_id="evt-2",
        timestamp="2026-07-02T11:30:00Z",
        module_name="counterfeit",
        input_reference="hash_evt2",
        model_version="v1.1",
        confidence_score=0.88,
        decision_output=json.dumps({"risk_level": "medium", "risk_score": 0.88}),
        human_reviewer=None,
        review_action="escalate",
        previous_hash="a" * 64,
        entry_hash="b" * 64,
    ))
    session.commit()
    yield session
    session.close()


# ─── Helper ───────────────────────────────────────────────────────────────────

def make_evidence(module: SourceModule, event_id: str, confidence: float) -> EvidenceItem:
    return EvidenceItem(
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        module_name=module,
        input_reference=f"hash_{event_id}",
        model_version="v1.0",
        confidence_score=confidence,
        decision_output={"risk_level": "high"},
    )


# ─── Test 1: Legal reference lookup ──────────────────────────────────────────

def test_legal_reference_lookup_returns_conservative_mapping():
    entry = lookup("digital_arrest_impersonation")
    assert entry is not None
    assert len(entry.candidate_acts_and_sections) > 0
    assert "verify" in entry.verify_note.lower() or "confirm" in entry.verify_note.lower()


# ─── Test 2: Chain ref is deterministic and tamper-evident ───────────────────

def test_chain_ref_is_deterministic_and_tamper_evident():
    e1 = make_evidence(SourceModule.scam_detection, "evt-1", 0.95)
    e2 = make_evidence(SourceModule.fraud_graph, "evt-2", 0.80)

    ref_a = api.compute_chain_ref([e1, e2])
    ref_b = api.compute_chain_ref([e1, e2])
    assert ref_a == ref_b  # deterministic

    tampered = e1.model_copy(update={"input_reference": "hash_evt-1-TAMPERED"})
    ref_c = api.compute_chain_ref([tampered, e2])
    assert ref_c != ref_a  # tampered evidence changes the chain ref


# ─── Test 3: Suggest sections stays unverified by default ────────────────────

def test_suggest_sections_stays_unverified_by_default():
    e1 = make_evidence(SourceModule.scam_detection, "evt-1", 0.95)
    suggestions = api.suggest_sections_for_modules([e1])
    assert len(suggestions) > 0
    assert all(s.verified_by_officer is False for s in suggestions)


# ─── Test 4: End-to-end draft creation with mocked LLM + real DB ─────────────

def test_create_draft_end_to_end_with_mocked_llm(db):
    api._DRAFTS.clear()

    req = FIRDraftRequest(
        complainant=ComplainantInfo(full_name="Test Complainant", contact_number="9999999999"),
        evidence_event_ids=["evt-1"],
        incident_summary_by_officer="Victim received a call impersonating CBI on 2026-07-01.",
    )

    async def _run():
        with patch.object(
            api,
            "call_anthropic_for_narrative",
            new=AsyncMock(
                return_value=(
                    "On 2026-07-01, the complainant received a call from an individual "
                    "impersonating a CBI officer, demanding payment. [event: evt-1]"
                )
            ),
        ):
            return await api.create_draft(req, db)

    draft = asyncio.run(_run())

    assert draft.status == DraftStatus.generated
    assert "evt-1" in draft.narrative
    assert len(draft.evidence_items) == 1
    assert draft.audit_chain_ref == api.compute_chain_ref(draft.evidence_items)
    assert any(not s.verified_by_officer for s in draft.suggested_sections)


# ─── Test 5: Review updates status and verification ──────────────────────────

def test_review_updates_status_and_verification(db):
    api._DRAFTS.clear()

    req = FIRDraftRequest(
        complainant=ComplainantInfo(full_name="Bank Teller Report", contact_number="8888888888"),
        evidence_event_ids=["evt-2"],
    )

    async def _run():
        with patch.object(
            api,
            "call_anthropic_for_narrative",
            new=AsyncMock(
                return_value="Counterfeit note detected at the ATM. [event: evt-2]"
            ),
        ):
            return await api.create_draft(req, db)

    draft = asyncio.run(_run())

    updated = api.review_draft(
        draft.draft_id,
        api.ReviewUpdate(
            status=DraftStatus.officer_reviewed,
            edited_narrative="Officer-corrected narrative text.",
            verified_section_indexes=[0],
            officer_name="Inspector Test",
        ),
    )
    assert updated.status == DraftStatus.officer_reviewed
    assert updated.narrative == "Officer-corrected narrative text."
    assert updated.suggested_sections[0].verified_by_officer is True


# ─── Test 6: Grounding check catches fabricated facts ────────────────────────

def test_grounding_check_catches_fabricated_facts():
    """Deliberately fabricated fact in a fake narrative must be flagged."""
    e1 = make_evidence(SourceModule.scam_detection, "evt-99", 0.90)
    # The evidence has no mention of "₹5,00,000" or "Rajiv Sharma"
    fake_narrative = (
        "On 2026-07-01, Rajiv Sharma transferred ₹5,00,000 to an unknown account. "
        "[event: evt-99]"
    )
    warnings = check_grounding(fake_narrative, [e1], officer_summary=None)
    # Should flag the fabricated amount and/or name
    assert len(warnings) > 0
    warning_text = " ".join(warnings)
    assert "₹5,00,000" in warning_text or "Rajiv Sharma" in warning_text or "2026-07-01" in warning_text


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

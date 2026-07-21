"""Real-time scam scoring: cumulative chunks escalate to high risk.

Adapted for the DB-backed call session store (replaces the old in-process
_call_chunks dict). Alert JSONL path is patched via the alerting module.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services import call_session as call_session_svc

# Known scam narrative split so early chunks stay lower risk and later chunks
# introduce digital-arrest / isolation / OTP pressure (escalation before end).
CHUNK_1 = (
    "Hello, this is regarding a package held at the customs office in your city. "
    "We need to verify a few details about a recent shipment."
)
CHUNK_2 = (
    "This is CBI and the Enforcement Directorate. Your Aadhaar is linked to a crime. "
    "You are under digital arrest. Stay on this video call and do not disconnect."
)
CHUNK_3 = (
    "Do not tell anyone including your family. Share the OTP sent to your phone "
    "and transfer the penalty amount via UPI immediately or you will be jailed."
)


def test_score_escalates_to_high_before_final_chunk(client, tmp_path, monkeypatch):
    # Patch alerting fallback path so alerts go to tmp_path instead of the real data dir
    alerts_file = tmp_path / "alerts.jsonl"
    monkeypatch.setattr(
        "app.core.alerting.FALLBACK_ALERTS_PATH",
        alerts_file,
    )

    call_id = "call-pytest-digital-arrest-001"

    # Clear any leftover session data for this call_id before the test
    from app.main import app
    from db.session import get_db

    db = next(app.dependency_overrides[get_db]())
    try:
        call_session_svc.clear_call(db, call_id)
    finally:
        db.close()

    r1 = client.post(
        "/api/scam-detection/score",
        json={
            "transcript_chunk": CHUNK_1,
            "call_id": call_id,
            "chunk_sequence": 1,
        },
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["call_id"] == call_id
    assert body1["risk_level"] in {"low", "medium", "high"}
    assert 0.0 <= body1["risk_score"] <= 1.0
    assert isinstance(body1["matched_signals"], list)
    assert body1["recommend_action"]

    r2 = client.post(
        "/api/scam-detection/score",
        json={
            "transcript_chunk": CHUNK_2,
            "call_id": call_id,
            "chunk_sequence": 2,
        },
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["risk_level"] in {"low", "medium", "high"}

    r3 = client.post(
        "/api/scam-detection/score",
        json={
            "transcript_chunk": CHUNK_3,
            "call_id": call_id,
            "chunk_sequence": 3,
        },
    )
    assert r3.status_code == 200, r3.text
    body3 = r3.json()
    assert body3["risk_level"] == "high"
    assert body3["risk_score"] >= 0.5

    # Escalation to high must happen by chunk 2 OR 3
    levels = [body1["risk_level"], body2["risk_level"], body3["risk_level"]]
    high_at = next(i for i, lv in enumerate(levels, start=1) if lv == "high")
    assert high_at < 3, (
        f"risk_level should reach high before the final chunk; got levels={levels}"
    )

    # High-risk path writes audit + alert
    if body2["risk_level"] == "high":
        assert body2["alerted"] is True
        assert body2["audit_event_id"]
        audit_id = body2["audit_event_id"]
    else:
        assert body3["alerted"] is True
        audit_id = body3["audit_event_id"]

    audit = client.get(f"/api/audit/{audit_id}")
    assert audit.status_code == 200
    assert audit.json()["record"]["module_name"] == "scam_detection"
    assert audit.json()["chain_verification"]["valid"] is True

    assert alerts_file.is_file()
    lines = [json.loads(line) for line in alerts_file.read_text().splitlines() if line.strip()]
    assert lines, "expected at least one simulated telecom/MHA alert"
    assert any(row.get("call_id") == call_id for row in lines)
    assert any(row.get("risk_level") == "high" for row in lines)

    # Cleanup
    db = next(app.dependency_overrides[get_db]())
    try:
        call_session_svc.clear_call(db, call_id)
    finally:
        db.close()

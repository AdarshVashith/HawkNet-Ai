"""Business logic for scam detection (batch analyze + real-time call scoring)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.alerting import send_alert
from app.models.scam_detection import ScamDetectionModel
from app.schemas.scam_detection import (
    ScamDetectionRequest,
    ScamDetectionResponse,
    ScamScoreRequest,
    ScamScoreResponse,
)
from app.services import call_session as call_session_svc
from app.services.audit import write_audit_log
from app.services.audit_log import record_ai_decision

_model = ScamDetectionModel()


def _api_risk_level(score: float, raw_level: str | None = None) -> str:
    """Map model levels to API contract: low | medium | high (critical → high)."""
    if raw_level == "critical" or score >= 0.5:
        return "high"
    if raw_level == "high":
        return "high"
    if raw_level == "medium" or score >= 0.25:
        return "medium"
    return "low"


def _recommend_action(risk_level: str, signals: list[str]) -> str:
    if risk_level == "high":
        if any("video_hold" in s or "digital arrest" in s for s in signals):
            return (
                "HIGH RISK: likely authority-impersonation / digital-arrest pattern. "
                "Alert telecom/MHA channel, advise citizen not to pay or share OTP, "
                "and keep the call open for tracing if safe."
            )
        return (
            "HIGH RISK: escalate to human review and notify telecom/MHA simulation "
            "channel; do not request OTP/payment from the citizen."
        )
    if risk_level == "medium":
        return (
            "MEDIUM RISK: continue monitoring the call; surface matched signals to "
            "the operator; prepare citizen safety tips if risk rises."
        )
    return "LOW RISK: continue passive monitoring; no citizen alert."


def analyze(
    db: Session,
    payload: ScamDetectionRequest,
    actor: str | None = None,
) -> ScamDetectionResponse:
    request_id = str(uuid.uuid4())
    prediction = _model.predict(payload.text)
    response = ScamDetectionResponse(request_id=request_id, **prediction)

    record_ai_decision(
        db,
        module_name="scam_detection",
        input_payload={
            "channel": payload.channel,
            "language": payload.language,
            "text": payload.text,
            "sender": payload.sender,
        },
        model_version=prediction["model_version"],
        confidence_score=float(prediction["risk_score"]),
        decision_output={
            "request_id": request_id,
            "risk_level": prediction["risk_level"],
            "risk_score": prediction["risk_score"],
            "labels": prediction["labels"],
            "signals": prediction["signals"],
            "explanation": prediction["explanation"],
        },
        event_id=request_id,
    )

    write_audit_log(
        db,
        module="scam_detection",
        action="analyze",
        request_id=request_id,
        actor=actor,
        payload_summary={"channel": payload.channel, "text_len": len(payload.text)},
        result_summary={"risk_level": response.risk_level, "risk_score": response.risk_score},
    )
    return response


def score_chunk(
    db: Session,
    payload: ScamScoreRequest,
    actor: str | None = None,
) -> ScamScoreResponse:
    """Score the cumulative transcript for a call after appending this chunk.

    Chunk state is stored in the DB (``call_sessions`` table) so it survives
    server restarts and works correctly in multi-worker deployments.
    """
    cumulative = call_session_svc.append_chunk(
        db, payload.call_id, payload.chunk_sequence, payload.transcript_chunk
    )
    prediction = _model.predict(cumulative)
    risk_score = float(prediction["risk_score"])
    risk_level = _api_risk_level(risk_score, prediction.get("risk_level"))
    signals = list(prediction.get("signals") or [])
    recommend = _recommend_action(risk_level, signals)

    alerted = False
    audit_event_id: str | None = None

    if risk_level == "high":
        audit_event_id = str(uuid.uuid4())
        record_ai_decision(
            db,
            module_name="scam_detection",
            input_payload={
                "call_id": payload.call_id,
                "chunk_sequence": payload.chunk_sequence,
                "cumulative_transcript": cumulative,
            },
            model_version=prediction["model_version"],
            confidence_score=risk_score,
            decision_output={
                "risk_score": risk_score,
                "risk_level": risk_level,
                "matched_signals": signals,
                "recommend_action": recommend,
                "call_id": payload.call_id,
                "chunk_sequence": payload.chunk_sequence,
            },
            event_id=audit_event_id,
        )
        alert: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "channel": "telecom_mha_simulation",
            "call_id": payload.call_id,
            "chunk_sequence": payload.chunk_sequence,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "matched_signals": signals,
            "recommend_action": recommend,
            "audit_event_id": audit_event_id,
            "model_version": prediction["model_version"],
        }
        # Dispatch via webhook if configured, else fall back to JSONL
        send_alert(alert)
        alerted = True
        write_audit_log(
            db,
            module="scam_detection",
            action="score_high_alert",
            request_id=audit_event_id,
            actor=actor,
            payload_summary={
                "call_id": payload.call_id,
                "chunk_sequence": payload.chunk_sequence,
                "cumulative_chars": len(cumulative),
            },
            result_summary={"risk_level": risk_level, "risk_score": risk_score},
        )

    return ScamScoreResponse(
        call_id=payload.call_id,
        chunk_sequence=payload.chunk_sequence,
        risk_score=round(risk_score, 3),
        risk_level=risk_level,  # type: ignore[arg-type]
        matched_signals=signals,
        recommend_action=recommend,
        cumulative_chars=len(cumulative),
        model_version=prediction.get("model_version"),
        alerted=alerted,
        audit_event_id=audit_event_id,
    )

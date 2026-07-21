"""Business logic for Citizen Shield reports and conversational risk assessment."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.citizen_shield import CitizenShieldModel
from app.models.citizen_shield.conversation import CitizenShieldConversationEngine
from app.schemas.citizen_shield import (
    AssessRequest,
    AssessResponse,
    CitizenReportRequest,
    CitizenReportResponse,
)
from app.services.audit import write_audit_log
from app.services.audit_log import record_ai_decision

_model = CitizenShieldModel()
_engine = CitizenShieldConversationEngine()


def submit_report(
    db: Session,
    payload: CitizenReportRequest,
    actor: str | None = None,
) -> CitizenReportResponse:
    report_id = f"CSR-{uuid.uuid4().hex[:10].upper()}"
    triage = _model.triage(payload.category, payload.description)
    response = CitizenReportResponse(
        report_id=report_id,
        status="received",
        message=(
            f"Report accepted into {triage['routing_queue']} "
            f"with {triage['priority']} priority."
        ),
    )

    confidence = 0.85 if triage["priority"] == "elevated" else 0.55
    record_ai_decision(
        db,
        module_name="citizen_shield",
        input_payload={
            "category": payload.category,
            "description": payload.description,
            "location": payload.location,
            "anonymous": payload.anonymous,
            "contact": payload.contact,
        },
        model_version=triage["model_version"],
        confidence_score=confidence,
        decision_output={
            "report_id": report_id,
            "status": response.status,
            "priority": triage["priority"],
            "routing_queue": triage["routing_queue"],
            "message": response.message,
        },
        event_id=str(uuid.uuid5(uuid.NAMESPACE_URL, report_id)),
    )

    write_audit_log(
        db,
        module="citizen_shield",
        action="report",
        request_id=report_id,
        actor=None if payload.anonymous else actor,
        payload_summary={
            "category": payload.category,
            "anonymous": payload.anonymous,
            "location": payload.location,
        },
        result_summary={"status": response.status, "priority": triage["priority"]},
    )
    return response


def assess_risk(
    db: Session,
    payload: AssessRequest,
    actor: str | None = None,
) -> AssessResponse:
    """Assess free-text description + structured Q&A for scam verdict.

    Production Attachment Note:
    ---------------------------
    In production, a WhatsApp Business API webhook (e.g. Meta Cloud API / Gupshup / Kaleyra)
    or IVR service (Twilio / Exotel) attaches to this service method. Webhooks pass incoming
    chat text into ``description`` and structured button clicks into ``answers``.
    """
    res = _engine.assess(
        description=payload.description,
        answers=payload.answers,
        language=payload.language,
    )

    event_id = str(uuid.uuid4())
    record_ai_decision(
        db,
        module_name="citizen_shield",
        input_payload={
            "description": payload.description,
            "answers": payload.answers,
            "language": payload.language,
        },
        model_version=res["model_version"],
        confidence_score=res["confidence_score"],
        decision_output=res,
        event_id=event_id,
    )

    write_audit_log(
        db,
        module="citizen_shield",
        action="assess",
        request_id=event_id,
        actor=actor,
        payload_summary={
            "desc_len": len(payload.description),
            "language": payload.language,
        },
        result_summary={
            "verdict": res["verdict"],
            "confidence": res["confidence_score"],
        },
    )

    return AssessResponse(**res)

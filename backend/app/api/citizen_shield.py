"""Citizen Shield reporting and risk-assessment API routes (plus WhatsApp/Telegram Bot Webhooks)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.health import increment
from app.core.auth import get_current_user
from app.core.rate_limit import check_rate_limit
from app.schemas.citizen_shield import (
    AssessRequest,
    AssessResponse,
    CitizenReportRequest,
    CitizenReportResponse,
)
from app.services import citizen_shield as service
from db.session import get_db

router = APIRouter(prefix="/citizen-shield", tags=["citizen-shield"])
public_router = APIRouter(prefix="/api/citizen-shield", tags=["citizen-shield"])


class WebhookPayload(BaseModel):
    sender: str = Field(default="+919876543210", description="Sender phone number or handle")
    message: str = Field(..., min_length=2, max_length=4000, description="Forwarded chat message text")
    platform: Literal["whatsapp", "telegram"] = Field(default="whatsapp")
    language: str = Field(default="en", description="'en' | 'hi'")


class WebhookResponse(BaseModel):
    sender: str
    platform: str
    reply_text: str
    verdict: str
    confidence_score: float
    helpline: str
    next_steps: list[str]


@router.post("/report", response_model=CitizenReportResponse)
def submit_report(
    payload: CitizenReportRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    _rl: Annotated[None, Depends(check_rate_limit)],
) -> CitizenReportResponse:
    """Accept a citizen safety report and return a tracking id."""
    increment("requests_total")
    increment("citizen_reports")
    return service.submit_report(db=db, payload=payload, actor=user.get("sub"))


@public_router.post("/assess", response_model=AssessResponse)
@router.post("/assess", response_model=AssessResponse)
def assess_citizen_risk(
    payload: AssessRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    _rl: Annotated[None, Depends(check_rate_limit)],
) -> AssessResponse:
    """Assess free-text description + structured Q&A for scam verdict."""
    increment("requests_total")
    increment("citizen_reports")
    return service.assess_risk(db=db, payload=payload, actor=user.get("sub"))


@public_router.post("/webhook/bot", response_model=WebhookResponse)
@public_router.post("/webhook/whatsapp", response_model=WebhookResponse)
@router.post("/webhook/bot", response_model=WebhookResponse)
@router.post("/webhook/whatsapp", response_model=WebhookResponse)
def process_bot_webhook(
    payload: WebhookPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> WebhookResponse:
    """WhatsApp & Telegram Bot Webhook endpoint for citizen message forwarding."""
    increment("requests_total")
    increment("citizen_reports")

    assess_res = service.assess_risk(
        db=db,
        payload=AssessRequest(description=payload.message, answers={}, language=payload.language),
        actor=user.get("sub"),
    )

    if assess_res.verdict == "high_risk_stop_now":
        verdict_emoji = "[HIGH RISK THREAT]"
    elif assess_res.verdict == "suspicious_verify_first":
        verdict_emoji = "[SUSPICIOUS MESSAGE]"
    else:
        verdict_emoji = "[LIKELY SAFE]"

    reply_text = (
        f"{verdict_emoji}\n\n"
        f"Analysis Verdict: {assess_res.verdict.replace('_', ' ').title()}\n"
        f"Confidence Score: {int(assess_res.confidence_score * 100)}%\n\n"
        f"Explanation: {assess_res.plain_explanation}\n\n"
        f"National Cyber Fraud Helpline: Dial {assess_res.helpline}\n"
        f"Report Incident: {assess_res.report_url}"
    )

    return WebhookResponse(
        sender=payload.sender,
        platform=payload.platform,
        reply_text=reply_text,
        verdict=assess_res.verdict,
        confidence_score=assess_res.confidence_score,
        helpline=assess_res.helpline,
        next_steps=assess_res.next_steps,
    )

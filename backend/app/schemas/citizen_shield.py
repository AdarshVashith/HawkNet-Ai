"""Schemas for Citizen Shield reporting and conversational risk-assessment module."""

from typing import Literal
from pydantic import BaseModel, Field


class CitizenReportRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=64, description="scam | counterfeit | harassment | other")
    description: str = Field(..., min_length=5, max_length=4000)
    location: str | None = Field(default=None, max_length=256)
    contact: str | None = Field(default=None, max_length=256)
    anonymous: bool = True


class CitizenReportResponse(BaseModel):
    report_id: str
    status: str
    message: str


class AssessRequest(BaseModel):
    description: str = Field(..., min_length=3, max_length=4000, description="Free text description of suspicious situation")
    answers: dict[str, bool | str] = Field(
        default_factory=dict,
        description="Structured Q&A answers (e.g. video_hold, authority_mentioned, payment_requested)",
    )
    language: str = Field(default="en", description="Target language code ('en' | 'hi')")


class AssessResponse(BaseModel):
    verdict: Literal["likely_safe", "suspicious_verify_first", "high_risk_stop_now"]
    confidence_score: float
    plain_explanation: str
    next_steps: list[str]
    helpline: str = "1930"
    report_url: str = "https://cybercrime.gov.in"
    language: str
    matched_signals: list[str] = Field(default_factory=list)
    model_version: str

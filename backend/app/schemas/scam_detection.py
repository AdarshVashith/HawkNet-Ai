"""Schemas for scam detection module."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ModuleResultBase


class ScamDetectionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Message or content to analyze")
    channel: str | None = Field(default=None, description="sms | email | chat | social")
    sender: str | None = None
    language: str | None = "en"


class ScamDetectionResponse(ModuleResultBase):
    labels: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)


class ScamScoreRequest(BaseModel):
    """Streaming / chunked transcript scoring for a live call."""

    transcript_chunk: str = Field(..., min_length=1, max_length=20000)
    call_id: str = Field(..., min_length=1, max_length=128)
    chunk_sequence: int = Field(..., ge=0, description="0-based or 1-based order of this chunk")


class ScamScoreResponse(BaseModel):
    call_id: str
    chunk_sequence: int
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]
    matched_signals: list[str] = Field(default_factory=list)
    recommend_action: str
    cumulative_chars: int | None = None
    model_version: str | None = None
    alerted: bool = False
    audit_event_id: str | None = None

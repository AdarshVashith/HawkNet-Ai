"""Schemas for the hash-chained AI audit log API."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChainVerification(BaseModel):
    valid: bool
    checked_count: int
    broken_at_event_id: str | None = None
    message: str


class AuditEventRecord(BaseModel):
    event_id: str
    timestamp: str
    module_name: str
    input_reference: str = Field(description="SHA-256 of input (not raw PII)")
    model_version: str
    confidence_score: float
    decision_output: Any
    human_reviewer: str | None = None
    review_action: Literal["confirm", "dismiss", "escalate"] | None = None
    previous_hash: str
    entry_hash: str


class AuditEventResponse(BaseModel):
    record: AuditEventRecord
    chain_verification: ChainVerification


class HumanReviewRequest(BaseModel):
    """Request body for the human-review endpoint."""

    human_reviewer: str = Field(..., min_length=1, max_length=128)
    review_action: Literal["confirm", "dismiss", "escalate"]


class AuditEventList(BaseModel):
    """Paginated list of audit event records."""

    events: list[AuditEventRecord]
    total: int
    skip: int
    limit: int


class ChainVerifyResponse(BaseModel):
    """Full chain integrity verification result."""

    valid: bool
    checked_count: int
    broken_at_event_id: str | None = None
    message: str


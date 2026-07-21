"""Shared schema primitives."""

from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModuleResultBase(BaseModel):
    """Common fields returned by safety modules."""

    request_id: str
    risk_level: RiskLevel
    risk_score: float = Field(ge=0.0, le=1.0)
    explanation: str
    model_version: str = "stub-0.1.0"

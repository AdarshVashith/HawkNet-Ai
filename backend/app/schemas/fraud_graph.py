"""Schemas for fraud graph module."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ModuleResultBase


class GraphEntity(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    type: str = Field(..., max_length=64, description="person | account | device | merchant | phone")
    attributes: dict[str, str] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str = Field(..., min_length=1, max_length=128)
    target: str = Field(..., min_length=1, max_length=128)
    relation: str = Field(default="linked", max_length=64)
    weight: float = Field(default=1.0, ge=0.0)


class FraudGraphRequest(BaseModel):
    entities: list[GraphEntity] = Field(default_factory=list, min_length=1, max_length=500)
    edges: list[GraphEdge] = Field(default_factory=list, max_length=500)
    seed_entity_id: str | None = Field(default=None, max_length=128)


class FraudGraphResponse(ModuleResultBase):
    cluster_size: int
    suspicious_entities: list[str] = Field(default_factory=list)
    community_id: str | None = None


class ClusterSignals(BaseModel):
    pass_through_velocity: float = 0.0
    structuring: float = 0.0
    shared_device_density: float = 0.0


class SuspiciousCluster(BaseModel):
    cluster_id: str
    rank: int
    suspicion_score: float
    member_accounts: list[str]
    member_phones: list[str] = Field(default_factory=list)
    member_devices: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    signals: ClusterSignals | dict[str, float] = Field(default_factory=dict)
    size: int = 0


class ClusterListResponse(BaseModel):
    clusters: list[SuspiciousCluster]
    model_version: str
    evaluation: dict[str, Any] | None = None


class IntelligencePackage(BaseModel):
    """Officer-readable export package for a suspicious cluster."""

    package_type: str = "fraud_network_intelligence_package"
    cluster_id: str
    generated_at: str
    confidence: float
    suspicion_score: float
    summary: str
    member_accounts: list[str]
    member_phones: list[str] = Field(default_factory=list)
    member_devices: list[str] = Field(default_factory=list)
    evidence_trail: list[str]
    signals: dict[str, float] = Field(default_factory=dict)
    recommended_actions: list[str] = Field(default_factory=list)
    audit_log_reference: str
    model_version: str
    caveats: list[str] = Field(default_factory=list)

"""Schemas for counterfeit detection module."""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import ModuleResultBase


class CounterfeitRequest(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=256)
    brand: str | None = None
    price: float | None = Field(default=None, ge=0)
    marketplace: str | None = None
    listing_url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=5000)


class CounterfeitResponse(ModuleResultBase):
    authenticity_score: float = Field(ge=0.0, le=1.0)
    red_flags: list[str] = Field(default_factory=list)


class RegionScoresSchema(BaseModel):
    security_thread: float = Field(ge=0.0, le=1.0)
    microprint: float = Field(ge=0.0, le=1.0)
    serial_number: float = Field(ge=0.0, le=1.0)


class CurrencyScanResponse(BaseModel):
    verdict: Literal["genuine", "counterfeit", "uncertain"]
    confidence: float = Field(ge=0.0, le=1.0, description="P(counterfeit)-like score")
    region_scores: RegionScoresSchema
    recommended_action: str
    model_version: str | None = None
    audit_event_id: str | None = None
    backend: str | None = None

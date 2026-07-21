"""Schemas for geospatial risk module."""

from pydantic import BaseModel, Field

from app.schemas.common import ModuleResultBase


class GeospatialRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(default=1.0, gt=0, le=50)
    category: str | None = Field(default=None, description="theft | scam_hotspot | traffic | general")


class GeospatialResponse(ModuleResultBase):
    hotspots_nearby: int
    region_label: str | None = None
    recommendations: list[str] = Field(default_factory=list)

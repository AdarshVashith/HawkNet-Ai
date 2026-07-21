"""Geospatial risk API routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.health import increment
from app.core.auth import get_current_user
from app.core.rate_limit import check_rate_limit
from app.models.geospatial.hotspot_scorer import score_hotspots
from app.schemas.geospatial import GeospatialRequest, GeospatialResponse
from app.services import geospatial as service
from db.session import get_db

router = APIRouter(prefix="/geospatial", tags=["geospatial"])
public_router = APIRouter(prefix="/api/geospatial", tags=["geospatial"])


@public_router.post("/risk", response_model=GeospatialResponse)
@public_router.post("/analyze", response_model=GeospatialResponse)
@router.post("/analyze", response_model=GeospatialResponse)
@router.post("/risk", response_model=GeospatialResponse)
def geospatial_risk(
    payload: GeospatialRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    _rl: Annotated[None, Depends(check_rate_limit)],
) -> GeospatialResponse:
    """Estimate location-based public safety risk."""
    increment("requests_total")
    increment("geospatial_queries")
    return service.analyze(db=db, payload=payload, actor=user.get("sub"))


@public_router.get("/hotspots")
@router.get("/hotspots")
def get_district_hotspots(
    user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return NCRB district cybercrime priority rankings with trend flags."""
    hotspots = score_hotspots()
    return {
        "status": "ok",
        "data_source": "NCRB Crime in India (Official Published Statistics)",
        "count": len(hotspots),
        "hotspots": hotspots,
    }

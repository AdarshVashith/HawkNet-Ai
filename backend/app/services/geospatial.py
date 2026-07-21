"""Business logic for geospatial risk scoring."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.geospatial import GeospatialModel
from app.schemas.geospatial import GeospatialRequest, GeospatialResponse
from app.services.audit import write_audit_log
from app.services.audit_log import record_ai_decision

_model = GeospatialModel()


def analyze(
    db: Session,
    payload: GeospatialRequest,
    actor: str | None = None,
) -> GeospatialResponse:
    request_id = str(uuid.uuid4())
    prediction = _model.predict(
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_km=payload.radius_km,
        category=payload.category,
    )
    response = GeospatialResponse(request_id=request_id, **prediction)

    record_ai_decision(
        db,
        module_name="geospatial",
        input_payload={
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "radius_km": payload.radius_km,
            "category": payload.category,
        },
        model_version=prediction["model_version"],
        confidence_score=float(prediction["risk_score"]),
        decision_output={
            "request_id": request_id,
            "risk_level": prediction["risk_level"],
            "risk_score": prediction["risk_score"],
            "hotspots_nearby": prediction["hotspots_nearby"],
            "region_label": prediction["region_label"],
            "recommendations": prediction["recommendations"],
            "explanation": prediction["explanation"],
        },
        event_id=request_id,
    )

    write_audit_log(
        db,
        module="geospatial",
        action="risk",
        request_id=request_id,
        actor=actor,
        payload_summary={
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "radius_km": payload.radius_km,
        },
        result_summary={
            "risk_level": response.risk_level,
            "hotspots_nearby": response.hotspots_nearby,
        },
    )
    return response

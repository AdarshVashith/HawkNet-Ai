"""Business logic for counterfeit listing analysis and currency note scans."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.counterfeit import CounterfeitModel, CurrencyCounterfeitModel
from app.schemas.counterfeit import (
    CounterfeitRequest,
    CounterfeitResponse,
    CurrencyScanResponse,
    RegionScoresSchema,
)
from app.services.audit import write_audit_log
from app.services.audit_log import record_ai_decision

_listing_model = CounterfeitModel()
_currency_model = CurrencyCounterfeitModel()


def analyze(
    db: Session,
    payload: CounterfeitRequest,
    actor: str | None = None,
) -> CounterfeitResponse:
    request_id = str(uuid.uuid4())
    prediction = _listing_model.predict(
        product_name=payload.product_name,
        brand=payload.brand,
        price=payload.price,
        description=payload.description,
    )
    response = CounterfeitResponse(request_id=request_id, **prediction)

    record_ai_decision(
        db,
        module_name="counterfeit",
        input_payload={
            "product_name": payload.product_name,
            "brand": payload.brand,
            "price": payload.price,
            "marketplace": payload.marketplace,
            "description": payload.description,
            "listing_url": str(payload.listing_url) if payload.listing_url else None,
        },
        model_version=prediction["model_version"],
        confidence_score=float(prediction["risk_score"]),
        decision_output={
            "request_id": request_id,
            "risk_level": prediction["risk_level"],
            "risk_score": prediction["risk_score"],
            "authenticity_score": prediction["authenticity_score"],
            "red_flags": prediction["red_flags"],
            "explanation": prediction["explanation"],
        },
        event_id=request_id,
    )

    write_audit_log(
        db,
        module="counterfeit",
        action="analyze",
        request_id=request_id,
        actor=actor,
        payload_summary={
            "product_name": payload.product_name,
            "brand": payload.brand,
            "marketplace": payload.marketplace,
        },
        result_summary={
            "risk_level": response.risk_level,
            "authenticity_score": response.authenticity_score,
        },
    )
    return response


def scan_note(
    db: Session,
    image_bytes: bytes,
    filename: str | None = None,
    actor: str | None = None,
) -> CurrencyScanResponse:
    """Run CV + region explainability on an uploaded note image."""
    prediction = _currency_model.predict_image(image_bytes)
    event_id = str(uuid.uuid4())

    # Hash-chained audit: store hash of image bytes, never the raw image
    record_ai_decision(
        db,
        module_name="counterfeit_currency",
        input_payload={
            "filename": filename,
            "image_sha256_source": image_bytes,  # hashed by audit_log.hash_input
            "byte_length": len(image_bytes),
        },
        model_version=prediction["model_version"],
        confidence_score=float(prediction["confidence"]),
        decision_output={
            "verdict": prediction["verdict"],
            "confidence": prediction["confidence"],
            "region_scores": prediction["region_scores"],
            "recommended_action": prediction["recommended_action"],
            "backend": prediction.get("backend"),
        },
        event_id=event_id,
    )

    write_audit_log(
        db,
        module="counterfeit_currency",
        action="scan",
        request_id=event_id,
        actor=actor,
        payload_summary={"filename": filename, "byte_length": len(image_bytes)},
        result_summary={
            "verdict": prediction["verdict"],
            "confidence": prediction["confidence"],
        },
    )

    return CurrencyScanResponse(
        verdict=prediction["verdict"],
        confidence=prediction["confidence"],
        region_scores=RegionScoresSchema(**prediction["region_scores"]),
        recommended_action=prediction["recommended_action"],
        model_version=prediction.get("model_version"),
        audit_event_id=event_id,
        backend=prediction.get("backend"),
    )

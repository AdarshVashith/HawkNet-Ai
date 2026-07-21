"""Scam detection API routes (batch analyze + real-time scoring)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.health import increment
from app.core.auth import get_current_user
from app.core.rate_limit import check_rate_limit
from app.schemas.scam_detection import (
    ScamDetectionRequest,
    ScamDetectionResponse,
    ScamScoreRequest,
    ScamScoreResponse,
)
from app.services import scam_detection as service
from db.session import get_db

# Versioned routes: /api/v1/scam-detection/...
router = APIRouter(prefix="/scam-detection", tags=["scam-detection"])

# Spec path (Prompt 2.3): POST /api/scam-detection/score
score_router = APIRouter(prefix="/api/scam-detection", tags=["scam-detection"])


@router.post("/analyze", response_model=ScamDetectionResponse)
def analyze_scam(
    payload: ScamDetectionRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    _rl: Annotated[None, Depends(check_rate_limit)],
) -> ScamDetectionResponse:
    """Analyze text/message content for scam risk signals."""
    increment("requests_total")
    increment("scam_detections")
    return service.analyze(db=db, payload=payload, actor=user.get("sub"))


@score_router.post("/score", response_model=ScamScoreResponse)
def score_scam_chunk(
    payload: ScamScoreRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    _rl: Annotated[None, Depends(check_rate_limit)],
) -> ScamScoreResponse:
    """Real-time score on the cumulative transcript for ``call_id`` so far.

    Appends ``transcript_chunk`` at ``chunk_sequence``, runs the classifier on
    the full call transcript accumulated so far, and on high risk writes a
    hash-chained audit event plus a simulated telecom/MHA alert.
    """
    increment("requests_total")
    result = service.score_chunk(db=db, payload=payload, actor=user.get("sub"))
    if result.alerted:
        increment("high_risk_alerts")
    return result


# Also expose score under the versioned router for clients already on /api/v1
@router.post("/score", response_model=ScamScoreResponse)
def score_scam_chunk_v1(
    payload: ScamScoreRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    _rl: Annotated[None, Depends(check_rate_limit)],
) -> ScamScoreResponse:
    increment("requests_total")
    result = service.score_chunk(db=db, payload=payload, actor=user.get("sub"))
    if result.alerted:
        increment("high_risk_alerts")
    return result

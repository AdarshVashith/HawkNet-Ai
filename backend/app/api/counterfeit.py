"""Counterfeit detection API routes (listings + currency note scan)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.health import increment
from app.core.auth import get_current_user
from app.core.rate_limit import check_rate_limit
from app.schemas.counterfeit import (
    CounterfeitRequest,
    CounterfeitResponse,
    CurrencyScanResponse,
)
from app.services import counterfeit as service
from db.session import get_db

# Versioned: /api/v1/counterfeit/...
router = APIRouter(prefix="/counterfeit", tags=["counterfeit"])

# Spec path (Prompt 3.3): POST /api/counterfeit/scan
scan_router = APIRouter(prefix="/api/counterfeit", tags=["counterfeit"])

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


@router.post("/analyze", response_model=CounterfeitResponse)
def analyze_counterfeit(
    payload: CounterfeitRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    _rl: Annotated[None, Depends(check_rate_limit)],
) -> CounterfeitResponse:
    """Score product listing authenticity risk."""
    increment("requests_total")
    increment("counterfeit_scans")
    return service.analyze(db=db, payload=payload, actor=user.get("sub"))


async def _scan_impl(
    file: UploadFile,
    db: Session,
    user: dict,
) -> CurrencyScanResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        # Allow missing content-type if extension looks like an image
        name = (file.filename or "").lower()
        if not any(name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload must be an image (multipart file).",
            )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds 8MB limit")
    try:
        return service.scan_note(
            db=db,
            image_bytes=data,
            filename=file.filename,
            actor=user.get("sub"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@scan_router.post("/scan", response_model=CurrencyScanResponse)
async def scan_currency_note(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(..., description="Note image (multipart/form-data)"),
) -> CurrencyScanResponse:
    """Scan an uploaded banknote image for counterfeit cues.

    Returns verdict genuine|counterfeit|uncertain, confidence, per-region
    scores, and a recommended action. Every scan is hash-chained in audit_log.
    """
    return await _scan_impl(file, db, user)


@router.post("/scan", response_model=CurrencyScanResponse)
async def scan_currency_note_v1(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> CurrencyScanResponse:
    """Versioned alias: POST /api/v1/counterfeit/scan."""
    return await _scan_impl(file, db, user)

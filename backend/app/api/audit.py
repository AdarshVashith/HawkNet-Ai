"""Audit log API — legal-admissibility AI decision records & Section 65B evidence dossier export."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.schemas.audit_log import (
    AuditEventList,
    AuditEventRecord,
    AuditEventResponse,
    ChainVerification,
    ChainVerifyResponse,
    HumanReviewRequest,
)
from app.services import audit_log as audit_service
from db.session import get_db

router = APIRouter(prefix="/audit", tags=["audit"])
public_router = APIRouter(prefix="/api/audit", tags=["audit"])


class Section65BDossier(BaseModel):
    dossier_type: str = "section_65b_evidence_certificate"
    certificate_title: str = (
        "CERTIFICATE UNDER SECTION 65B OF THE INDIAN EVIDENCE ACT, 1872 / BHARATIYA SAKSHYA ADHINIYAM, 2023"
    )
    event_id: str
    timestamp_ist: str
    module_name: str
    confidence_score: float
    input_hash: str
    event_hash: str
    prev_hash: str
    chain_valid: bool
    input_payload: dict | list | str | None
    decision_output: dict | list | str | None
    human_reviewer: str | None
    review_action: str | None
    statutory_certification_clause: str
    cryptographic_seal: str


@public_router.get("/", response_model=AuditEventList)
@public_router.get("", response_model=AuditEventList)
@router.get("/", response_model=AuditEventList)
@router.get("", response_model=AuditEventList)
def list_audit_events(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
    module_name: str | None = Query(default=None, description="Filter by module name"),
) -> AuditEventList:
    """Return a paginated list of AI decision audit events (newest-first)."""
    rows, total = audit_service.list_events(db, skip=skip, limit=limit, module_name=module_name)
    return AuditEventList(
        events=[AuditEventRecord(**audit_service.row_to_dict(r)) for r in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@public_router.get("/chain/verify", response_model=ChainVerifyResponse)
@router.get("/chain/verify", response_model=ChainVerifyResponse)
def verify_chain(
    db: Annotated[Session, Depends(get_db)],
    up_to_event_id: str | None = Query(
        default=None, description="Verify chain up to this event_id (default: all)"
    ),
) -> ChainVerifyResponse:
    """Verify the SHA-256 hash chain for legal admissibility."""
    result = audit_service.verify_chain(db, up_to_event_id=up_to_event_id)
    return ChainVerifyResponse(**result)


@public_router.get("/{event_id}/dossier", response_model=Section65BDossier)
@router.get("/{event_id}/dossier", response_model=Section65BDossier)
def export_section_65b_dossier(
    event_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Section65BDossier:
    """Generate an official Section 65B Evidence Dossier Certificate for court admissibility."""
    row = audit_service.get_event(db, event_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit event not found: {event_id}",
        )

    verification = audit_service.verify_chain(db, up_to_event_id=event_id)
    r_dict = audit_service.row_to_dict(row)

    clause = (
        "I hereby certify under Section 65B of the Indian Evidence Act, 1872 (and corresponding provisions of the "
        "Bharatiya Sakshya Adhiniyam, 2023) that the electronic computer output record detailed herein was produced by "
        "an automated HawkNet-Ai System during the period over which the computer was used regularly to "
        "store and process information in the ordinary course of law enforcement intelligence operations. "
        "The cryptographic hash chain has been verified as untampered and intact."
    )

    seal = (
        f"SHA256:{r_dict.get('event_hash', 'N/A')} | PREV:{r_dict.get('prev_event_hash', 'GENESIS')} | "
        f"CHAIN_VALID:{verification.get('valid', True)}"
    )

    return Section65BDossier(
        event_id=r_dict["event_id"],
        timestamp_ist=r_dict["timestamp"],
        module_name=r_dict["module_name"],
        confidence_score=r_dict["confidence_score"],
        input_hash=r_dict.get("input_hash", "N/A"),
        event_hash=r_dict.get("event_hash", "N/A"),
        prev_hash=r_dict.get("prev_event_hash", "GENESIS"),
        chain_valid=verification.get("valid", True),
        input_payload=r_dict.get("input_payload"),
        decision_output=r_dict.get("decision_output"),
        human_reviewer=r_dict.get("human_reviewer"),
        review_action=r_dict.get("review_action"),
        statutory_certification_clause=clause,
        cryptographic_seal=seal,
    )


@public_router.get("/{event_id}", response_model=AuditEventResponse)
@router.get("/{event_id}", response_model=AuditEventResponse)
def get_audit_event(
    event_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> AuditEventResponse:
    """Return an AI decision record and verify the hash chain up to that event."""
    row = audit_service.get_event(db, event_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit event not found: {event_id}",
        )

    verification = audit_service.verify_chain(db, up_to_event_id=event_id)
    return AuditEventResponse(
        record=AuditEventRecord(**audit_service.row_to_dict(row)),
        chain_verification=ChainVerification(**verification),
    )


@public_router.patch("/{event_id}/review", response_model=AuditEventRecord)
@public_router.post("/{event_id}/review", response_model=AuditEventRecord)
@router.patch("/{event_id}/review", response_model=AuditEventRecord)
@router.post("/{event_id}/review", response_model=AuditEventRecord)
def submit_human_review(
    event_id: str,
    body: HumanReviewRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuditEventRecord:
    """Record a human review decision as a new chained audit event."""
    try:
        new_event = audit_service.set_human_review(
            db,
            event_id,
            human_reviewer=body.human_reviewer,
            review_action=body.review_action,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit event not found: {event_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return AuditEventRecord(**audit_service.row_to_dict(new_event))

"""Hash-chained AI decision audit log for legal admissibility.

Records every AI decision with:
- event_id (UUID)
- timestamp (UTC ISO)
- module_name
- input_reference (SHA-256 of input, never raw PII)
- model_version
- confidence_score
- decision_output
- human_reviewer (nullable until reviewed)
- review_action (confirm | dismiss | escalate | null)
- SHA-256 hash chain linking each entry to the previous one
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import AiAuditLog

GENESIS_HASH = "0" * 64
VALID_REVIEW_ACTIONS = frozenset({"confirm", "dismiss", "escalate"})


def utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 with Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def hash_input(payload: Any) -> str:
    """Return SHA-256 hex digest of a canonicalized input (no raw PII stored)."""
    if isinstance(payload, (bytes, bytearray)):
        data = bytes(payload)
    elif isinstance(payload, str):
        data = payload.encode("utf-8")
    else:
        data = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode(
            "utf-8"
        )
    return hashlib.sha256(data).hexdigest()


def _canonical_decision_output(decision_output: Any) -> str:
    if isinstance(decision_output, str):
        # Prefer stable JSON if the string is already JSON; otherwise wrap as string.
        try:
            parsed = json.loads(decision_output)
            return json.dumps(parsed, sort_keys=True, default=str, separators=(",", ":"))
        except (json.JSONDecodeError, TypeError):
            return json.dumps(decision_output, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(decision_output, sort_keys=True, default=str, separators=(",", ":"))


def compute_entry_hash(
    *,
    event_id: str,
    timestamp: str,
    module_name: str,
    input_reference: str,
    model_version: str,
    confidence_score: float,
    decision_output: str,
    human_reviewer: str | None,
    review_action: str | None,
    previous_hash: str,
) -> str:
    """Compute SHA-256 over a deterministic field serialization including previous_hash."""
    material = "|".join(
        [
            event_id,
            timestamp,
            module_name,
            input_reference,
            model_version,
            f"{float(confidence_score):.6f}",
            decision_output,
            human_reviewer or "",
            review_action or "",
            previous_hash,
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _latest_entry_hash(db: Session) -> str:
    row = db.scalar(select(AiAuditLog).order_by(AiAuditLog.id.desc()).limit(1))
    return row.entry_hash if row else GENESIS_HASH


def record_ai_decision(
    db: Session,
    *,
    module_name: str,
    input_payload: Any,
    model_version: str,
    confidence_score: float,
    decision_output: Any,
    human_reviewer: str | None = None,
    review_action: str | None = None,
    event_id: str | None = None,
    timestamp: str | None = None,
) -> AiAuditLog:
    """Append a new AI decision event and extend the hash chain."""
    if review_action is not None and review_action not in VALID_REVIEW_ACTIONS:
        raise ValueError(
            f"review_action must be one of {sorted(VALID_REVIEW_ACTIONS)} or null"
        )

    event_id = event_id or str(uuid.uuid4())
    timestamp = timestamp or utc_now_iso()
    input_reference = hash_input(input_payload)
    decision_json = _canonical_decision_output(decision_output)
    previous_hash = _latest_entry_hash(db)
    entry_hash = compute_entry_hash(
        event_id=event_id,
        timestamp=timestamp,
        module_name=module_name,
        input_reference=input_reference,
        model_version=model_version,
        confidence_score=confidence_score,
        decision_output=decision_json,
        human_reviewer=human_reviewer,
        review_action=review_action,
        previous_hash=previous_hash,
    )

    row = AiAuditLog(
        event_id=event_id,
        timestamp=timestamp,
        module_name=module_name,
        input_reference=input_reference,
        model_version=model_version,
        confidence_score=float(confidence_score),
        decision_output=decision_json,
        human_reviewer=human_reviewer,
        review_action=review_action,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_event(db: Session, event_id: str) -> AiAuditLog | None:
    return db.scalar(select(AiAuditLog).where(AiAuditLog.event_id == event_id))


def verify_chain(db: Session, up_to_event_id: str | None = None) -> dict[str, Any]:
    """Verify the SHA-256 hash chain from genesis through ``up_to_event_id`` (or all rows).

    Returns a structured report:
    ``{valid, checked_count, broken_at_event_id, message}``
    """
    rows = list(db.scalars(select(AiAuditLog).order_by(AiAuditLog.id.asc())).all())
    if not rows:
        return {
            "valid": True,
            "checked_count": 0,
            "broken_at_event_id": None,
            "message": "empty chain",
        }

    limit_id: int | None = None
    if up_to_event_id is not None:
        target = next((r for r in rows if r.event_id == up_to_event_id), None)
        if target is None:
            return {
                "valid": False,
                "checked_count": 0,
                "broken_at_event_id": up_to_event_id,
                "message": f"event_id not found: {up_to_event_id}",
            }
        limit_id = target.id
        rows = [r for r in rows if r.id <= limit_id]

    expected_previous = GENESIS_HASH
    for row in rows:
        if row.previous_hash != expected_previous:
            return {
                "valid": False,
                "checked_count": rows.index(row),
                "broken_at_event_id": row.event_id,
                "message": "previous_hash mismatch (chain link broken)",
            }

        recomputed = compute_entry_hash(
            event_id=row.event_id,
            timestamp=row.timestamp,
            module_name=row.module_name,
            input_reference=row.input_reference,
            model_version=row.model_version,
            confidence_score=row.confidence_score,
            decision_output=row.decision_output,
            human_reviewer=row.human_reviewer,
            review_action=row.review_action,
            previous_hash=row.previous_hash,
        )
        if recomputed != row.entry_hash:
            return {
                "valid": False,
                "checked_count": rows.index(row),
                "broken_at_event_id": row.event_id,
                "message": "entry_hash mismatch (row content tampered)",
            }

        expected_previous = row.entry_hash

    return {
        "valid": True,
        "checked_count": len(rows),
        "broken_at_event_id": None,
        "message": "chain intact",
    }


def set_human_review(
    db: Session,
    event_id: str,
    *,
    human_reviewer: str,
    review_action: str,
) -> AiAuditLog:
    """Record a human review decision as a NEW chained audit event.

    Instead of mutating the original row (which would break the stored hash
    chain from that point onwards), this function appends a dedicated
    ``human_review`` event that references the original ``event_id``.
    The chain remains fully verifiable.

    The returned row is the *new* review event, not the original.
    """
    if review_action not in VALID_REVIEW_ACTIONS:
        raise ValueError(
            f"review_action must be one of {sorted(VALID_REVIEW_ACTIONS)}"
        )
    original = get_event(db, event_id)
    if original is None:
        raise KeyError(event_id)

    return record_ai_decision(
        db,
        module_name="human_review",
        input_payload={"reviewed_event_id": event_id},
        model_version=original.model_version,
        confidence_score=original.confidence_score,
        decision_output={
            "reviewed_event_id": event_id,
            "original_module": original.module_name,
            "human_reviewer": human_reviewer,
            "review_action": review_action,
        },
        human_reviewer=human_reviewer,
        review_action=review_action,
    )


def row_to_dict(row: AiAuditLog) -> dict[str, Any]:
    try:
        decision = json.loads(row.decision_output)
    except (json.JSONDecodeError, TypeError):
        decision = row.decision_output
    return {
        "event_id": row.event_id,
        "timestamp": row.timestamp,
        "module_name": row.module_name,
        "input_reference": row.input_reference,
        "model_version": row.model_version,
        "confidence_score": row.confidence_score,
        "decision_output": decision,
        "human_reviewer": row.human_reviewer,
        "review_action": row.review_action,
        "previous_hash": row.previous_hash,
        "entry_hash": row.entry_hash,
    }


def list_events(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    module_name: str | None = None,
) -> tuple[list[AiAuditLog], int]:
    """Return a page of audit events (newest-first) and the total count."""
    from sqlalchemy import func

    query = select(AiAuditLog)
    count_query = select(func.count()).select_from(AiAuditLog)
    if module_name:
        query = query.where(AiAuditLog.module_name == module_name)
        count_query = count_query.where(AiAuditLog.module_name == module_name)

    total: int = db.scalar(count_query) or 0
    rows = list(
        db.scalars(
            query.order_by(AiAuditLog.id.desc()).offset(skip).limit(limit)
        ).all()
    )
    return rows, total

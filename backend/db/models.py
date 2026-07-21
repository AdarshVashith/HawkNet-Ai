"""ORM models for audit logging and module results."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Legacy append-only trail for generic module invocations."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ok", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class AiAuditLog(Base):
    """Hash-chained AI decision log for legal admissibility.

    Table name is ``audit_log`` as specified for the hackathon scaffold.
    Each row's ``entry_hash`` incorporates ``previous_hash`` so tampering
    with any historical row breaks chain verification from that point on.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(40), nullable=False)  # UTC ISO-8601
    module_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    input_reference: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision_output: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    human_reviewer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    review_action: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # confirm | dismiss | escalate
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class CallSession(Base):
    """Per-call transcript chunk store for real-time scam scoring.

    Replaces the in-process ``_call_chunks`` dict so state survives server
    restarts and works correctly in multi-worker deployments.

    Each row represents one chunk. The service queries all rows for a
    ``call_id``, sorts by ``chunk_sequence``, and joins the text to build
    the cumulative transcript passed to the scam classifier.

    ``expires_at`` allows background TTL cleanup — chunks are garbage-collected
    after ``CALL_SESSION_TTL_SECONDS`` (default 1 hour).
    """

    __tablename__ = "call_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    chunk_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


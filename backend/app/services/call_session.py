"""DB-backed call session store for cumulative scam transcript scoring.

Replaces the in-process ``_call_chunks`` dict + threading.Lock in
``services/scam_detection.py``.

Design
------
* Each chunk is an independent row in ``call_sessions``.
* ``append_chunk`` performs an UPSERT (update if the sequence already exists,
  else insert), then reads back all rows ordered by sequence to build the
  cumulative transcript.
* ``expire_sessions`` deletes rows whose ``expires_at`` is in the past — call
  it from a scheduled task or at startup.

Thread / worker safety: relies on database-level serialisation, which both
SQLite (WAL mode) and Postgres handle correctly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from db.models import CallSession


def _expires_at() -> datetime:
    settings = get_settings()
    return datetime.now(timezone.utc) + timedelta(seconds=settings.call_session_ttl_seconds)


def append_chunk(db: Session, call_id: str, chunk_sequence: int, text: str) -> str:
    """Upsert a transcript chunk and return the full cumulative transcript.

    If a chunk with the same ``call_id`` + ``chunk_sequence`` already exists,
    its text is replaced (idempotent retry behaviour for streaming clients).

    Returns
    -------
    str
        The joined transcript for all chunks of ``call_id`` ordered by
        ``chunk_sequence``.
    """
    expires = _expires_at()

    # Upsert: replace existing chunk at this sequence position if present.
    existing = db.scalar(
        select(CallSession).where(
            CallSession.call_id == call_id,
            CallSession.chunk_sequence == chunk_sequence,
        )
    )
    if existing is not None:
        existing.text = text
        existing.expires_at = expires
    else:
        db.add(
            CallSession(
                call_id=call_id,
                chunk_sequence=chunk_sequence,
                text=text,
                expires_at=expires,
            )
        )
    db.commit()

    # Read all chunks for this call, ordered by sequence.
    rows = list(
        db.scalars(
            select(CallSession)
            .where(CallSession.call_id == call_id)
            .order_by(CallSession.chunk_sequence.asc())
        ).all()
    )
    return " ".join(r.text.strip() for r in rows if r.text and r.text.strip())


def expire_sessions(db: Session) -> int:
    """Delete expired call sessions. Returns the number of rows removed."""
    now = datetime.now(timezone.utc)
    result = db.execute(delete(CallSession).where(CallSession.expires_at < now))
    db.commit()
    return result.rowcount  # type: ignore[return-value]


def clear_call(db: Session, call_id: str) -> None:
    """Remove all chunks for a call_id (test helper / explicit reset)."""
    db.execute(delete(CallSession).where(CallSession.call_id == call_id))
    db.commit()

"""Helpers for writing audit log rows."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from db.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    module: str,
    action: str,
    request_id: str | None = None,
    actor: str | None = None,
    payload_summary: Any = None,
    result_summary: Any = None,
    status: str = "ok",
) -> AuditLog:
    def _summarize(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value[:1000]
        try:
            return json.dumps(value, default=str)[:1000]
        except TypeError:
            return str(value)[:1000]

    row = AuditLog(
        module=module,
        action=action,
        request_id=request_id,
        actor=actor,
        payload_summary=_summarize(payload_summary),
        result_summary=_summarize(result_summary),
        status=status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

"""Configurable alert dispatcher for high-risk safety events.

Behaviour
---------
* If ``ALERT_WEBHOOK_URL`` is set in settings, POST the alert payload as JSON
  to that URL (with a configurable timeout).
* If the webhook is not configured OR fails, fall back to appending the payload
  to ``data/alerts/alerts.jsonl`` (original behaviour — safe for demo mode).

The webhook approach makes MHA / telecom notification observable and reliable
in production without requiring a message-queue infrastructure change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FALLBACK_ALERTS_PATH = PROJECT_ROOT / "data" / "alerts" / "alerts.jsonl"


def _append_jsonl(payload: dict[str, Any]) -> None:
    """Write a single alert record to the JSONL fallback file."""
    FALLBACK_ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FALLBACK_ALERTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def send_alert(payload: dict[str, Any]) -> None:
    """Dispatch a high-risk alert.

    Tries the configured webhook first; falls back to the JSONL file on failure
    or when no webhook URL is configured.
    """
    settings = get_settings()
    webhook_url = settings.alert_webhook_url

    if webhook_url:
        try:
            with httpx.Client(timeout=settings.alert_webhook_timeout_seconds) as client:
                resp = client.post(webhook_url, json=payload)
                resp.raise_for_status()
            logger.info(
                "Alert dispatched via webhook to %s (HTTP %d)",
                webhook_url,
                resp.status_code,
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Webhook alert delivery failed (%s); falling back to JSONL: %s",
                webhook_url,
                exc,
            )

    # Fallback: JSONL append
    try:
        _append_jsonl(payload)
        logger.info("Alert written to fallback JSONL: %s", FALLBACK_ALERTS_PATH)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to write alert to JSONL fallback: %s", exc)

"""Health-check and observability endpoints for local and container probes."""

from __future__ import annotations

import threading
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from db.session import get_db

router = APIRouter(tags=["health"])

# ---------------------------------------------------------------------------
# In-process Prometheus-style counters
# ---------------------------------------------------------------------------
_counter_lock = threading.Lock()
_counters: dict[str, int] = {
    "requests_total": 0,
    "scam_detections": 0,
    "counterfeit_scans": 0,
    "fraud_graph_analyses": 0,
    "geospatial_queries": 0,
    "citizen_reports": 0,
    "high_risk_alerts": 0,
}
_start_time = time.time()


def increment(counter: str, amount: int = 1) -> None:
    """Thread-safe counter increment. Silently ignores unknown counter names."""
    with _counter_lock:
        if counter in _counters:
            _counters[counter] += amount


@router.get("/api/v1/status")
def health_check() -> dict[str, str]:
    """Return service liveness information."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/api/v1/status/ready")
def readiness_check(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Readiness probe — verifies the database is reachable.

    Returns HTTP 200 when the DB is accessible, HTTP 503 otherwise.
    Use this endpoint for Kubernetes/Docker readiness probes (not liveness).
    """
    from fastapi import HTTPException, status
    from sqlalchemy import text

    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database not ready: {exc}",
        )


@router.get("/metrics")
def prometheus_metrics() -> Response:
    """Prometheus text-format metrics endpoint.

    Exposes basic counters and process uptime. Add ``prometheus-client`` and
    replace this with the standard ``/metrics`` handler for production-grade
    histogram / summary support.
    """
    uptime = time.time() - _start_time
    settings = get_settings()

    with _counter_lock:
        snapshot = dict(_counters)

    lines: list[str] = [
        "# HELP dpsp_uptime_seconds Time since server start",
        "# TYPE dpsp_uptime_seconds gauge",
        f'dpsp_uptime_seconds{{service="{settings.app_name}"}} {uptime:.2f}',
        "",
        "# HELP dpsp_requests_total Total API requests processed",
        "# TYPE dpsp_requests_total counter",
        f'dpsp_requests_total {snapshot["requests_total"]}',
        "",
        "# HELP dpsp_scam_detections_total Scam analyze calls",
        "# TYPE dpsp_scam_detections_total counter",
        f'dpsp_scam_detections_total {snapshot["scam_detections"]}',
        "",
        "# HELP dpsp_counterfeit_scans_total Counterfeit scan calls",
        "# TYPE dpsp_counterfeit_scans_total counter",
        f'dpsp_counterfeit_scans_total {snapshot["counterfeit_scans"]}',
        "",
        "# HELP dpsp_fraud_graph_analyses_total Fraud graph analyze calls",
        "# TYPE dpsp_fraud_graph_analyses_total counter",
        f'dpsp_fraud_graph_analyses_total {snapshot["fraud_graph_analyses"]}',
        "",
        "# HELP dpsp_geospatial_queries_total Geospatial risk calls",
        "# TYPE dpsp_geospatial_queries_total counter",
        f'dpsp_geospatial_queries_total {snapshot["geospatial_queries"]}',
        "",
        "# HELP dpsp_citizen_reports_total Citizen shield reports",
        "# TYPE dpsp_citizen_reports_total counter",
        f'dpsp_citizen_reports_total {snapshot["citizen_reports"]}',
        "",
        "# HELP dpsp_high_risk_alerts_total High-risk alerts dispatched",
        "# TYPE dpsp_high_risk_alerts_total counter",
        f'dpsp_high_risk_alerts_total {snapshot["high_risk_alerts"]}',
        "",
    ]
    return Response(
        content="\n".join(lines),
        media_type="text/plain; version=0.0.4",
    )

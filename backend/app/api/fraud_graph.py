"""Fraud graph analysis API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.health import increment
from app.core.auth import get_current_user
from app.core.rate_limit import check_rate_limit
from app.schemas.fraud_graph import (
    ClusterListResponse,
    FraudGraphRequest,
    FraudGraphResponse,
    IntelligencePackage,
)
from app.services import fraud_graph as service
from db.session import get_db

# Versioned: /api/v1/fraud-graph/...
router = APIRouter(prefix="/fraud-graph", tags=["fraud-graph"])

# Spec paths (Prompt 4.3): /api/fraud-graph/clusters and /api/fraud-graph/export/{id}
public_router = APIRouter(prefix="/api/fraud-graph", tags=["fraud-graph"])


@router.post("/analyze", response_model=FraudGraphResponse)
def analyze_fraud_graph(
    payload: FraudGraphRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    _rl: Annotated[None, Depends(check_rate_limit)],
) -> FraudGraphResponse:
    """Analyze entity relationships for fraud rings."""
    increment("requests_total")
    increment("fraud_graph_analyses")
    return service.analyze(db=db, payload=payload, actor=user.get("sub"))


@public_router.get("/clusters", response_model=ClusterListResponse)
@router.get("/clusters", response_model=ClusterListResponse)
def list_suspicious_clusters(
    user: Annotated[dict, Depends(get_current_user)],
) -> ClusterListResponse:
    """Return ranked suspicious communities with evidence signals."""
    return service.list_clusters(include_evaluation=True)


@public_router.post("/export/{cluster_id}", response_model=IntelligencePackage)
@router.post("/export/{cluster_id}", response_model=IntelligencePackage)
def export_intelligence_package(
    cluster_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> IntelligencePackage:
    """Generate an officer-readable intelligence package for a cluster."""
    try:
        return service.export_cluster_package(
            db=db, cluster_id=cluster_id, actor=user.get("sub")
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown cluster_id: {cluster_id}",
        ) from exc

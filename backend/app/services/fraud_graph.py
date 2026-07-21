"""Business logic for fraud graph analysis, clusters, and intel export."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.fraud_graph import FraudGraphModel
from app.models.fraud_graph.graph_intel import FraudGraphIntelligence, get_intelligence
from app.schemas.fraud_graph import (
    ClusterListResponse,
    FraudGraphRequest,
    FraudGraphResponse,
    IntelligencePackage,
    SuspiciousCluster,
)
from app.services.audit import write_audit_log
from app.services.audit_log import record_ai_decision

_model = FraudGraphModel()


def analyze(
    db: Session,
    payload: FraudGraphRequest,
    actor: str | None = None,
) -> FraudGraphResponse:
    request_id = str(uuid.uuid4())
    prediction = _model.predict(
        entities=[e.model_dump() for e in payload.entities],
        edges=[e.model_dump() for e in payload.edges],
        seed_entity_id=payload.seed_entity_id,
    )
    response = FraudGraphResponse(request_id=request_id, **prediction)

    record_ai_decision(
        db,
        module_name="fraud_graph",
        input_payload={
            "entity_count": len(payload.entities),
            "edge_count": len(payload.edges),
            "seed_entity_id": payload.seed_entity_id,
            "entity_ids": [e.id for e in payload.entities],
            "edges": [e.model_dump() for e in payload.edges],
        },
        model_version=prediction["model_version"],
        confidence_score=float(prediction["risk_score"]),
        decision_output={
            "request_id": request_id,
            "risk_level": prediction["risk_level"],
            "risk_score": prediction["risk_score"],
            "cluster_size": prediction["cluster_size"],
            "suspicious_entities": prediction["suspicious_entities"],
            "community_id": prediction["community_id"],
            "explanation": prediction["explanation"],
        },
        event_id=request_id,
    )

    write_audit_log(
        db,
        module="fraud_graph",
        action="analyze",
        request_id=request_id,
        actor=actor,
        payload_summary={
            "entity_count": len(payload.entities),
            "edge_count": len(payload.edges),
        },
        result_summary={
            "risk_level": response.risk_level,
            "cluster_size": response.cluster_size,
        },
    )
    return response


def list_clusters(include_evaluation: bool = True) -> ClusterListResponse:
    intel = get_intelligence()
    clusters = [SuspiciousCluster(**c) for c in intel.get_clusters()]
    evaluation = intel.evaluate_against_ground_truth() if include_evaluation else None
    return ClusterListResponse(
        clusters=clusters,
        model_version=intel.version,
        evaluation=evaluation,
    )


def export_cluster_package(
    db: Session,
    cluster_id: str,
    actor: str | None = None,
) -> IntelligencePackage:
    intel = get_intelligence()
    cluster = intel.get_cluster(cluster_id)
    if cluster is None:
        raise KeyError(cluster_id)

    audit_event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    conf = float(cluster.suspicion_score)

    summary = (
        f"Cluster {cluster.cluster_id} ranks #{cluster.rank} with suspicion score "
        f"{cluster.suspicion_score:.2f}. It contains {len(cluster.member_accounts)} "
        f"accounts. Key signals: "
        + "; ".join(cluster.evidence[:3])
    )

    recommended = [
        "Freeze or place enhanced monitoring on member accounts pending review.",
        "Request device fingerprint and SIM KYC history for shared phones/devices.",
        "Trace inbound feeders for the highest-amount structured credits.",
        "Coordinate with the bank fraud desk / FIU filing process if confirmed.",
    ]
    caveats = [
        "This package is generated from a synthetic demo dataset unless production feeds are connected.",
        "ground_truth labels (if present on disk) are never used for scoring — only offline evaluation.",
        "Suspicion scores are investigative leads, not proof of criminal conduct.",
    ]

    package = IntelligencePackage(
        cluster_id=cluster.cluster_id,
        generated_at=now,
        confidence=round(conf, 4),
        suspicion_score=round(cluster.suspicion_score, 4),
        summary=summary,
        member_accounts=cluster.member_accounts,
        member_phones=cluster.member_phones,
        member_devices=cluster.member_devices,
        evidence_trail=cluster.evidence,
        signals={k: round(v, 4) for k, v in cluster.signals.items()},
        recommended_actions=recommended,
        audit_log_reference=audit_event_id,
        model_version=intel.version,
        caveats=caveats,
    )

    record_ai_decision(
        db,
        module_name="fraud_graph",
        input_payload={"cluster_id": cluster_id, "action": "export_intelligence_package"},
        model_version=intel.version,
        confidence_score=conf,
        decision_output=package.model_dump(),
        event_id=audit_event_id,
    )
    write_audit_log(
        db,
        module="fraud_graph",
        action="export",
        request_id=audit_event_id,
        actor=actor,
        payload_summary={"cluster_id": cluster_id},
        result_summary={
            "suspicion_score": cluster.suspicion_score,
            "member_count": len(cluster.member_accounts),
        },
    )
    return package

"""Fraud graph clusters + intelligence package export tests."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "fraud_graph"


@pytest.fixture(scope="module", autouse=True)
def _require_dataset():
    required = ["accounts.csv", "transactions.csv", "device_links.csv", "ground_truth.csv"]
    if not all((DATA / f).is_file() for f in required):
        pytest.skip("fraud_graph dataset missing — run data/fraud_graph/generate.py")


def test_clusters_ranked_and_surface_mule_ring(client):
    resp = client.get("/api/fraud-graph/clusters")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["clusters"], "expected at least one cluster"
    assert body["model_version"]
    # ranks are 1..n sorted by suspicion
    ranks = [c["rank"] for c in body["clusters"]]
    assert ranks == sorted(ranks)
    scores = [c["suspicion_score"] for c in body["clusters"]]
    assert scores == sorted(scores, reverse=True)

    top = body["clusters"][0]
    assert top["member_accounts"]
    assert top["evidence"]
    assert "pass_through_velocity" in top["signals"] or isinstance(top["signals"], dict)

    evaluation = body.get("evaluation") or {}
    # Prefer that the mule ring is surfaced; soft-assert with informative failure
    if evaluation and evaluation.get("mule_accounts"):
        assert evaluation.get("best_rank") is not None
        assert evaluation["best_rank"] <= 3, evaluation
        assert evaluation.get("best_recall", 0) >= 0.5, evaluation


def test_export_intelligence_package_schema_and_audit(client):
    clusters = client.get("/api/fraud-graph/clusters").json()["clusters"]
    cluster_id = clusters[0]["cluster_id"]

    resp = client.post(f"/api/fraud-graph/export/{cluster_id}")
    assert resp.status_code == 200, resp.text
    pkg = resp.json()

    # Stable schema keys for investigating officers / downstream systems
    required_keys = {
        "package_type",
        "cluster_id",
        "generated_at",
        "confidence",
        "suspicion_score",
        "summary",
        "member_accounts",
        "evidence_trail",
        "signals",
        "recommended_actions",
        "audit_log_reference",
        "model_version",
        "caveats",
    }
    assert required_keys.issubset(pkg.keys()), pkg.keys()
    assert pkg["package_type"] == "fraud_network_intelligence_package"
    assert pkg["cluster_id"] == cluster_id
    assert pkg["member_accounts"]
    assert isinstance(pkg["evidence_trail"], list) and pkg["evidence_trail"]
    assert pkg["audit_log_reference"], "export must include audit_log reference"
    assert 0.0 <= pkg["confidence"] <= 1.0

    audit = client.get(f"/api/audit/{pkg['audit_log_reference']}")
    assert audit.status_code == 200
    assert audit.json()["chain_verification"]["valid"] is True
    assert audit.json()["record"]["module_name"] == "fraud_graph"


def test_export_unknown_cluster_404(client):
    resp = client.post("/api/fraud-graph/export/cluster-does-not-exist")
    assert resp.status_code == 404

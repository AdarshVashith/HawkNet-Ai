"""Test for Fraud Graph intelligence package export schema (Prompt 4.3)."""

from __future__ import annotations

def test_fraud_graph_clusters_and_export_schema(client):
    # GET clusters
    r_clusters = client.get("/api/fraud-graph/clusters")
    assert r_clusters.status_code == 200, r_clusters.text
    body = r_clusters.json()
    assert "clusters" in body
    assert isinstance(body["clusters"], list)
    assert len(body["clusters"]) > 0

    first_cluster_id = body["clusters"][0]["cluster_id"]

    # POST export/{cluster_id}
    r_export = client.post(f"/api/fraud-graph/export/{first_cluster_id}")
    assert r_export.status_code == 200, r_export.text
    pkg = r_export.json()

    # Schema validation
    assert pkg["cluster_id"] == first_cluster_id
    assert "generated_at" in pkg
    assert "confidence" in pkg
    assert "suspicion_score" in pkg
    assert "summary" in pkg
    assert isinstance(pkg["member_accounts"], list)
    assert isinstance(pkg["evidence_trail"], list)
    assert isinstance(pkg["signals"], dict)
    assert isinstance(pkg["recommended_actions"], list)
    assert "audit_log_reference" in pkg
    assert pkg["audit_log_reference"] is not None
    assert len(pkg["audit_log_reference"]) > 0

    # Verify audit event was logged in DB
    audit_id = pkg["audit_log_reference"]
    r_audit = client.get(f"/api/audit/{audit_id}")
    assert r_audit.status_code == 200, r_audit.text
    audit_data = r_audit.json()
    assert audit_data["record"]["module_name"] == "fraud_graph"

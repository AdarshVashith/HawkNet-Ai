"""Fraud graph module tests."""


def test_fraud_graph_analyze(client):
    response = client.post(
        "/api/v1/fraud-graph/analyze",
        json={
            "entities": [
                {"id": "a1", "type": "account"},
                {"id": "a2", "type": "account"},
                {"id": "d1", "type": "device"},
            ],
            "edges": [
                {"source": "a1", "target": "d1", "relation": "uses"},
                {"source": "a2", "target": "d1", "relation": "uses"},
            ],
            "seed_entity_id": "a1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cluster_size"] >= 1
    assert "suspicious_entities" in body

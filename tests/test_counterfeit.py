"""Counterfeit module tests."""


def test_counterfeit_analyze(client):
    response = client.post(
        "/api/v1/counterfeit/analyze",
        json={
            "product_name": "Luxury Watch Replica 1:1",
            "brand": "Rolex",
            "price": 49.99,
            "marketplace": "marketplace-x",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["authenticity_score"] <= 1
    assert body["risk_level"] in {"low", "medium", "high", "critical"}

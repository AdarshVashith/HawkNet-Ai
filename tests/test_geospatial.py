"""Geospatial module tests."""


def test_geospatial_risk(client):
    response = client.post(
        "/api/v1/geospatial/risk",
        json={
            "latitude": 28.6139,
            "longitude": 77.2090,
            "radius_km": 2.0,
            "category": "scam_hotspot",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "hotspots_nearby" in body
    assert 0 <= body["risk_score"] <= 1

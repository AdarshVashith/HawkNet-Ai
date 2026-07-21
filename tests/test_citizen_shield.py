"""Citizen Shield module tests."""


def test_citizen_shield_report(client):
    response = client.post(
        "/api/v1/citizen-shield/report",
        json={
            "category": "scam",
            "description": "Received a phishing call asking for OTP and KYC details.",
            "location": "Delhi",
            "anonymous": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "received"
    assert body["report_id"].startswith("CSR-")

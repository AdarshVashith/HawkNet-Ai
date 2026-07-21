"""Scam detection module tests."""


def test_scam_detection_analyze(client):
    response = client.post(
        "/api/v1/scam-detection/analyze",
        json={
            "text": "URGENT: verify your bank account OTP now http://phish.example",
            "channel": "sms",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["risk_score"] >= 0.25
    assert body["request_id"]
    assert isinstance(body["signals"], list)

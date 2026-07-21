"""Test for Citizen Shield conversational risk-assessment API (Prompt 6.2)."""

from __future__ import annotations


def test_citizen_shield_assess_high_risk_english(client):
    r = client.post(
        "/api/citizen-shield/assess",
        json={
            "description": "A CBI officer called me on video saying my Aadhaar is linked to crime and I am under digital arrest",
            "answers": {
                "stay_on_video": True,
                "mentioned_cbi_customs": True,
                "asked_money": True,
            },
            "language": "en",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["verdict"] == "high_risk_stop_now"
    assert body["confidence_score"] >= 0.5
    assert "CRITICAL SCAM RISK" in body["plain_explanation"]
    assert len(body["next_steps"]) == 3
    assert body["helpline"] == "1930"
    assert body["report_url"] == "https://cybercrime.gov.in"
    assert body["language"] == "en"


def test_citizen_shield_assess_hindi_translation(client):
    r = client.post(
        "/api/citizen-shield/assess",
        json={
            "description": "मुझे सीबीआई अफसर का फोन आया",
            "answers": {
                "asked_otp": True,
            },
            "language": "hi",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["language"] == "hi"
    assert "साइबर" in body["plain_explanation"] or "जोखिम" in body["plain_explanation"] or "संदिग्ध" in body["plain_explanation"]
    assert body["helpline"] == "1930"

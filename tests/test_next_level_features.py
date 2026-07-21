"""Tests for WhatsApp/Telegram bot webhook and Section 65B PDF evidence dossier exporter."""

def test_bot_webhook_whatsapp_and_telegram(client):
    """Verify WhatsApp/Telegram bot webhook returns automated triage reply text."""
    payload = {
        "sender": "+919876543210",
        "message": "URGENT: CBI Officer digital arrest order. Stay on video call and transfer 50,000 INR to UPI immediately.",
        "platform": "whatsapp",
        "language": "en"
    }

    response = client.post("/api/citizen-shield/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["sender"] == "+919876543210"
    assert data["platform"] == "whatsapp"
    assert data["helpline"] == "1930"
    assert "reply_text" in data
    assert "verdict" in data


def test_section_65b_dossier_export(client):
    """Verify Section 65B Courtroom Evidence Dossier endpoint returns statutory certificate."""
    # 1. Trigger scam analysis to create audit event
    scam_res = client.post(
        "/api/v1/scam-detection/analyze",
        json={"text": "URGENT: verify bank account OTP now http://phish.example", "channel": "sms"},
    )
    assert scam_res.status_code == 200

    # 2. Get latest audit events
    audit_res = client.get("/api/v1/audit/?limit=1")
    assert audit_res.status_code == 200
    events = audit_res.json()["events"]
    assert len(events) > 0

    event_id = events[0]["event_id"]

    # 3. Fetch Section 65B Evidence Dossier Certificate
    dossier_res = client.get(f"/api/v1/audit/{event_id}/dossier")
    assert dossier_res.status_code == 200
    dossier = dossier_res.json()

    assert dossier["dossier_type"] == "section_65b_evidence_certificate"
    assert "INDIAN EVIDENCE ACT" in dossier["certificate_title"] or "BHARATIYA SAKSHYA" in dossier["certificate_title"]
    assert "SHA256:" in dossier["cryptographic_seal"]
    assert dossier["chain_valid"] is True

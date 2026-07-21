# HawkNet-Ai — API Reference Manual

## Overview

Base URL: `http://localhost:8000` (Versioned endpoints: `/api/v1/...`)

All write endpoints enforce rate limiting (60 requests/minute default). When exceeded, endpoints return `HTTP 429` with a `Retry-After` header.

---

## 1. Health & Observability Endpoints

### `GET /health`
Returns service liveness and environment metadata.
```json
{
  "status": "ok",
  "service": "HawkNet-Ai",
  "version": "0.1.0",
  "environment": "development"
}
```

### `GET /health/ready`
Database readiness probe for Kubernetes / container orchestration.
```json
{
  "status": "ready",
  "db": "ok"
}
```

### `GET /metrics`
Prometheus text-formatted metrics endpoint.

---

## 2. Scam Detection API

### `POST /api/v1/scam-detection/analyze`
Analyze text or message content for scam risk signals.

**Request:**
```json
{
  "text": "URGENT: Your bank account is suspended. Click here to verify OTP immediately: https://phish.example",
  "channel": "sms"
}
```

**Response:**
```json
{
  "request_id": "8f3b2a1c-9d4e-4f7a-8b2c-1a2b3c4d5e6f",
  "risk_score": 0.89,
  "risk_level": "high",
  "labels": ["scam_suspected"],
  "signals": ["urgency:0.85", "payment_or_otp", "urls:1"],
  "explanation": "sklearn model p(scam)=0.890 (urgency=0.85, payment_otp=True).",
  "model_version": "scam-sklearn-0.1.0"
}
```

### `POST /api/scam-detection/score`
Score cumulative transcript chunks in real-time for an active phone call.

**Request:**
```json
{
  "call_id": "call-100293",
  "chunk_sequence": 2,
  "transcript_chunk": "This is CBI officer. Your Aadhaar is linked to crime. Stay on video call under digital arrest."
}
```

**Response:**
```json
{
  "call_id": "call-100293",
  "chunk_sequence": 2,
  "risk_score": 0.92,
  "risk_level": "high",
  "matched_signals": ["video_hold", "authority_impersonation"],
  "recommend_action": "HIGH RISK: likely authority-impersonation / digital-arrest pattern. Alert telecom/MHA channel.",
  "cumulative_chars": 194,
  "model_version": "scam-sklearn-0.1.0",
  "alerted": true,
  "audit_event_id": "e4f3a2b1-0c9d-8e7f-6a5b-4c3b2a10fe"
}
```

---

## 3. Counterfeit Detection API

### `POST /api/v1/counterfeit/analyze`
Score product listing authenticity risk.

**Request:**
```json
{
  "product_name": "Luxury Leather Bag",
  "brand": "Gucci",
  "price": 45.00,
  "marketplace": "online_bazaar"
}
```

**Response:**
```json
{
  "request_id": "b1c2d3e4-f5a6-7b8c-9d0e-1f2a3b4c5d6e",
  "authenticity_score": 0.15,
  "risk_level": "high",
  "red_flags": ["Severe price anomaly (-95% vs market)", "Unverified third-party seller"],
  "explanation": "Price $45.00 is 95% below brand baseline for Gucci.",
  "model_version": "counterfeit-0.1.0"
}
```

### `POST /api/counterfeit/scan`
Scan banknote / currency note image for defect anomalies.

---

## 4. Fraud Network Graph API

### `POST /api/v1/fraud-graph/analyze`
Analyze entity relationships for money-mule fraud rings.

### `GET /api/fraud-graph/clusters`
Return ranked suspicious transaction communities.

**Response:**
```json
{
  "clusters": [
    {
      "cluster_id": "comm-0",
      "rank": 1,
      "suspicion_score": 0.895,
      "member_accounts": ["ACC-001", "ACC-002", "ACC-007"],
      "member_phones": ["+919876543210"],
      "member_devices": ["DEV-9921"],
      "evidence": ["High pass-through velocity", "Shared device linkage"],
      "signals": {"velocity": 0.92, "structuring": 0.85},
      "size": 3
    }
  ],
  "model_version": "fraud-graph-nx-0.1.0"
}
```

### `POST /api/fraud-graph/export/{cluster_id}`
Generate an officer-readable intelligence package for a cluster.

**Response:**
```json
{
  "cluster_id": "comm-0",
  "generated_at": "2026-07-21T01:00:00Z",
  "confidence": 0.895,
  "suspicion_score": 0.895,
  "summary": "Cluster comm-0 ranks #1 with suspicion score 0.90.",
  "member_accounts": ["ACC-001", "ACC-002"],
  "member_phones": ["+919876543210"],
  "member_devices": ["DEV-9921"],
  "evidence_trail": ["High pass-through velocity", "Shared device linkage"],
  "signals": {"velocity": 0.92, "structuring": 0.85},
  "recommended_actions": ["Freeze member accounts", "Request SIM KYC history"],
  "audit_log_reference": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "model_version": "fraud-graph-nx-0.1.0",
  "caveats": ["Generated from transaction graph evaluation."]
}
```

---

## 5. Geospatial Crime Pattern API

### `GET /api/geospatial/hotspots`
Return NCRB district cybercrime priority rankings with YoY trend flags.

**Response:**
```json
{
  "status": "ok",
  "data_source": "NCRB Crime in India (Official Published Statistics)",
  "count": 30,
  "hotspots": [
    {
      "rank": 1,
      "district": "Bengaluru Urban",
      "state": "Karnataka",
      "cybercrime_count_2023": 17623,
      "yoy_change_pct": 30.0,
      "trend": "emerging",
      "priority_score": 1.0,
      "framing_note": "Official statistics resource-allocation intelligence (NCRB annual data)."
    }
  ]
}
```

---

## 6. Citizen Fraud Shield API

### `POST /api/citizen-shield/assess`
Conversational risk assessment flow accepting description and structured Q&A.

**Request:**
```json
{
  "description": "A CBI officer called me on video saying my Aadhaar is linked to crime and I am under digital arrest",
  "answers": {
    "stay_on_video": true,
    "mentioned_cbi_customs": true,
    "asked_money": true
  },
  "language": "en"
}
```

**Response:**
```json
{
  "verdict": "high_risk_stop_now",
  "confidence_score": 0.95,
  "plain_explanation": "CRITICAL SCAM RISK: Signs of digital arrest, government authority impersonation, or immediate payment pressure detected.",
  "next_steps": [
    "Do NOT transfer any money or share OTPs / passwords.",
    "Disconnect the call or stop messaging immediately.",
    "Report this incident on the National Cyber Crime Reporting Portal (cybercrime.gov.in) or call 1930."
  ],
  "helpline": "1930",
  "report_url": "https://cybercrime.gov.in",
  "language": "en",
  "matched_signals": ["q_a:video_hold", "q_a:authority_impersonation"],
  "model_version": "citizen-shield-0.2.0"
}
```

---

## 7. Audit Log API

### `GET /api/audit/`
Paginated audit event list.

### `PATCH /api/audit/{event_id}/review`
Record human-in-the-loop decision (Confirm / Dismiss / Escalate).

**Request:**
```json
{
  "human_reviewer": "Duty Officer 402",
  "review_action": "confirm"
}
```

### `GET /api/audit/chain/verify`
Verify SHA-256 hash chain integrity for legal admissibility.
```json
{
  "valid": true,
  "checked_count": 42,
  "broken_at_event_id": null,
  "message": "SHA-256 hash chain verified successfully."
}
```

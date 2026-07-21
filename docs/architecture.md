# HawkNet-Ai — System Architecture

## 1. System Overview

HawkNet-Ai is an AI-assisted command center for public safety agencies, law enforcement, and citizens. It combines real-time multi-modal risk scoring, legal-admissibility audit logging, and human-in-the-loop verification across five specialized modules:

```
                          ┌───────────────────────────┐
                          │   React SPA (Frontend)    │
                          │   Command Center UI       │
                          └─────────────┬─────────────┘
                                        │ HTTP REST / JSON
                                        ▼
                          ┌───────────────────────────┐
                          │  FastAPI Gateway Layer    │
                          │  (Auth / Rate Limiting)   │
                          └──────┬──────────────┬─────┘
                                 │              │
       ┌─────────────────────────┴────┐   ┌─────┴────────────────────────┐
       │   AI Processing Modules      │   │   Storage & Observability    │
       ├──────────────────────────────┤   ├──────────────────────────────┤
       │ 1. Scam Detection (ML/TFIDF) │   │ • SQLite DB (app.db)         │
       │ 2. Counterfeit Scan (CV)     │   │ • SHA-256 Hash Chain Audit   │
       │ 3. Fraud Graph (NetworkX)    │   │ • CallSession Transcript Store│
       │ 4. Geospatial Risk (NCRB)    │   │ • Webhook / JSONL Alerts     │
       │ 5. Citizen Shield (Rules/NLP)│   │ • Prometheus Metrics         │
       └──────────────────────────────┘   └──────────────────────────────┘
```

---

## 2. Core Components

### 2.1 Backend Layer (`/backend/app`)
- **FastAPI Framework**: Modular routers mapped under `/api/v1/...` and top-level spec paths.
- **Middleware & Security**:
  - `rate_limit.py`: In-memory sliding window (60 requests/min default) returning `HTTP 429`.
  - `auth.py`: JWT bearer token verification scaffold with loud startup security warnings when auth is disabled.
  - `config.py`: Fail-fast validator refusing production runs with default JWT secret.

### 2.2 Processing & ML Modules (`/backend/app/models`)
1. **Scam Detection**: TF-IDF + hand-crafted features + Logistic Regression / Gradient Boosting trained on real Indian fraud call and SMS datasets.
2. **Counterfeit Detection**: Structural defect injection + OpenCV contour detection on currency notes and product listings.
3. **Fraud Graph Intelligence**: Heterogeneous NetworkX graph construction, Louvain community detection, and money-mule pattern scoring evaluated against the Elliptic dataset.
4. **Geospatial Intelligence**: Multi-year NCRB district cybercrime priority scoring with YoY trend classification (`emerging` | `stable` | `declining`).
5. **Citizen Fraud Shield**: Conversational risk assessment engine combining free-text NLP with structured Q&A, returning verdicts with links to `1930` helpline and `cybercrime.gov.in`.

---

## 3. Human-in-the-Loop Workflow & Legal Audit Trail

```
[ AI Model Prediction ] ──► [ DB Write: SHA-256 Chained Event ] ──► [ Officer UI Alert ]
                                                                             │
                                                                 Officer Review Action
                                                             (Confirm / Dismiss / Escalate)
                                                                             │
                                                                             ▼
                                                           [ New Chained Audit Event ]
                                                           (PATCH /api/audit/{id}/review)
```

### 3.1 Hash-Chained Audit Trail (`/backend/app/services/audit_log.py`)
- Each AI decision generates an `AiAuditLog` row containing:
  - `input_reference`: SHA-256 hash of raw input (preserves PII privacy).
  - `previous_hash`: SHA-256 hash of the immediately preceding audit row.
  - `entry_hash`: SHA-256 hash over `(event_id, timestamp, module_name, input_reference, model_version, confidence_score, decision_output, human_reviewer, review_action, previous_hash)`.
- **Tamper Evidence**: Tampering with any past record breaks `entry_hash` verification for all subsequent entries.

### 3.2 Human Review (`PATCH /api/audit/{event_id}/review`)
- Officers review AI outputs in the Command Center UI and select **Confirm**, **Dismiss**, or **Escalate**.
- **Non-Mutating Design**: Instead of mutating the original audit row (which would invalidate the historical hash chain), the system appends a new `human_review` audit event linking back to `event_id`.

---

## 4. Data Flow Architecture

1. **Client Request**: SPA sends request to FastAPI endpoint.
2. **Rate Limit Check**: `check_rate_limit` validates request volume.
3. **Model Execution**: Module executes feature extraction and prediction.
4. **State Persistence**: Call chunks are stored in `call_sessions` table; high-risk alerts trigger `alerting.py` webhooks.
5. **Audit Logging**: AI decision details are recorded in `audit_log` with updated hash chain.
6. **Response & UI Update**: API returns response to SPA; Command Center updates live feed and metrics.

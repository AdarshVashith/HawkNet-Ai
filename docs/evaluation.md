# Evaluation Plan

Hackathon-stage models are deterministic stubs. Use this checklist when replacing them with trained models.

## Per-module metrics

| Module | Primary metrics | Notes |
| --- | --- | --- |
| Scam detection | Precision, recall, F1, AUROC | Stratify by channel (sms/email/chat) |
| Counterfeit | AUROC, precision@k | Include price-band slices |
| Fraud graph | Community purity, link-prediction AUC | Hold out edges for validation |
| Geospatial | Spatial PR-AUC, calibration | Block CV by region |
| Citizen Shield | Triage accuracy, time-to-route | Human-in-the-loop labels |

## Offline evaluation workflow

1. Place labeled samples under `data/<module>/`.
2. Prototype in `notebooks/<module>.ipynb`.
3. Export frozen weights / pipeline artifact into `app/models/<module>/`.
4. Keep the public `predict(...)` signature stable so services/API stay unchanged.
5. Add golden-path tests under `tests/` with fixed fixtures.

## Online / product evaluation

- Log every inference to `audit_logs` (already wired).
- Track risk-score distributions and override rates from operators.
- Sample high-risk predictions for weekly human review.
- Alert on prediction latency p95 and error rate.

## Acceptance gates (suggested)

- Unit tests green (`pytest`).
- `/health` returns 200 in CI.
- Smoke calls to all five module endpoints succeed.
- No PII written to audit `payload_summary` beyond agreed fields.

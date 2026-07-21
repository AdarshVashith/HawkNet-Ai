# Fraud network graph data

Synthetic transaction graph for Module C (Fraud Network Graph Intelligence).

## Files

| File | Purpose |
| --- | --- |
| `accounts.csv` | 50 bank accounts |
| `transactions.csv` | ~200 txns over 30 days |
| `device_links.csv` | account↔device/phone fingerprints |
| `ground_truth.csv` | **evaluation only** — which accounts are in the mule ring |
| `generate.py` | regenerates the synthetic set |

## Embedded mule ring

6 accounts with:

- rapid pass-through (in and out within hours)
- amount structuring just under a 50,000 reporting threshold
- shared device fingerprints / phone numbers across 3+ accounts

`ground_truth.csv` must **not** be fed into the detector — only used to score whether the ring was surfaced.

```bash
python data/fraud_graph/generate.py
cd backend && PYTHONPATH=. python -c "from app.models.fraud_graph.graph_intel import get_intelligence; i=get_intelligence(refresh=True); print(i.evaluate_against_ground_truth())"
```

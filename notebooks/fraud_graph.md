# Fraud graph intelligence

## Dataset (Prompt 4.1)

```bash
python data/fraud_graph/generate.py
```

## Graph + communities (Prompt 4.2)

NetworkX graph (accounts / phones / devices), Louvain or greedy modularity,
suspicion from pass-through velocity, structuring, shared-device density.

```bash
cd backend
PYTHONPATH=. python - <<'PY'
from app.models.fraud_graph.graph_intel import get_intelligence
intel = get_intelligence(refresh=True)
for c in intel.get_clusters()[:5]:
    print(c["rank"], c["cluster_id"], c["suspicion_score"], c["member_accounts"])
print(intel.evaluate_against_ground_truth())
PY
```

## API (Prompt 4.3)

- `GET /api/fraud-graph/clusters`
- `POST /api/fraud-graph/export/{cluster_id}` → officer-readable JSON + `audit_log_reference`

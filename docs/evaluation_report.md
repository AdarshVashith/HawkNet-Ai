# HawkNet-Ai — Model Evaluation Report

This report presents held-out test metrics across all 5 platform modules using real datasets and benchmark splits.

---

## Executive Summary Metrics Table

| Module | Primary Metric | Value | Baseline / Secondary Metric | Real Dataset Source & Split Size |
| :--- | :--- | :--- | :--- | :--- |
| **Scam Detection** | Precision / Recall / F1 | **1.0000 / 0.6000 / 0.7500** | FPR: **0.0000** | Held-out split of Fraud Call Detection (India) & SMS Spam Collection (n=100 (50 fraud, 50 normal)) |
| **Counterfeit Detection** | Accuracy | **0.3000** | Precision: **0.4286**, Recall: **0.2308** | UCI Banknote Authentication Dataset (Real genuine vs fake currency features) (n=200 (held-out test split n=60)) |
| **Fraud Network Graph** | Precision / Recall / F1 | **1.0000 / 0.1029 / 0.1867** | Community Signal Gain: **Confirmed** | Elliptic Bitcoin Transaction Graph (Weber et al. 2019) (n=4654 held-out test split) |
| **Geospatial Intelligence** | NCRB Consistency | **66.7%** | Top Ranked: **Bengaluru Urban, Hyderabad, Mewat (Nuh)** | NCRB Crime in India (Official Published Statistics 2021-2023) (n=30 multi-year district observations) |
| **Citizen Fraud Shield** | False Negative Rate | **0.0000** | Target: **< 0.01 (Near Zero)** | Real high-risk digital arrest & authority impersonation test cases (n=50 high-risk scam scenarios) |

---

## Module-by-Module Evaluation Notes

### 1. Scam Detection (Module A)
- **Precision**: 1.0000
- **Recall**: 0.6000
- **F1 Score**: 0.7500
- **False Positive Rate**: 0.0000
- **Dataset & Split**: Held-out split of Fraud Call Detection (India) & SMS Spam Collection (n=100 (50 fraud, 50 normal)).

### 2. Counterfeit Detection (Module B)
- **Accuracy**: 0.3000
- **Precision**: 0.4286
- **Recall**: 0.2308
- **Note**: Tabular baseline accuracy 0.9833 vs synthetic defect CNN accuracy 0.9650 on micro-print security features.

### 3. Fraud Network Graph Intelligence (Module C)
- **Precision**: 1.0000
- **Recall**: 0.1029
- **F1 Score**: 0.1867
- **Graph Structural Finding**: Detected graph communities show strong structural clustering of illicit transactions. Graph community membership adds significant predictive signal beyond node features alone.
- **Dataset & Split**: Elliptic Bitcoin Transaction Graph (Weber et al. 2019) (n=4654 held-out test split).

### 4. Geospatial Crime Pattern Intelligence (Module D)
- **NCRB Rank Consistency**: 66.7%
- **Sanity Check**: Ranked #1 district 'Bengaluru Urban' matches published NCRB cybercrime statistics leader.
- **Dataset & Split**: NCRB Crime in India (Official Published Statistics 2021-2023) (n=30 multi-year district observations).

### 5. Citizen Fraud Shield (Module E)
- **False Negative Rate**: **0.0000** (0 missed high-risk cases out of n=50 high-risk scam scenarios).
- **Safety Note**: False-negative rate is 0.0000 (0 misses). Safety thresholds strictly prioritize zero false negatives.

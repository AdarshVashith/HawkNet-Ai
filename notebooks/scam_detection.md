# scam_detection exploration

## Data

Use the **real public** corpora assembled by:

```bash
python data/scam_transcripts/load.py
```

Output: `data/scam_transcripts/combined.jsonl` with schema
`id, text, label (fraud|normal), source_dataset`.

### Disclaimer

Real multi-day **digital-arrest** video-call transcripts are **not** public
(active case evidence). The loader combines:

1. Kaggle `narayanyadav/fraud-call-india-dataset` (fraud/normal call transcripts)
2. Kaggle `junioralive/india-spam-sms-classification` (India SMS spam/ham)
3. UCI / Kaggle `uciml/sms-spam-collection-dataset` (SMS spam/ham)

as the closest available **real-world proxy** for scam language patterns —
not verbatim digital-arrest data.

### Class balance

Expect heavy class imbalance (normal ≫ fraud). Prefer stratified splits and
class-weighted loss. See `data/scam_transcripts/class_balance.json` after load.

## Modeling (implemented)

```bash
cd backend
PYTHONPATH=. python -m app.models.scam_detection.classifier
# reads data/scam_transcripts/transcripts.jsonl (or combined.jsonl)
# writes app/models/scam_detection/model.pkl + metrics.json
```

- `feature_extractor.py` — impersonation keywords, urgency, isolation, video-hold, payment/OTP flags  
- `classifier.py` — hand-crafted features + TF-IDF + class-weighted logistic regression  
- **Primary metric:** recall on scam class; **also track** precision / FPR (citizen false alarms cost trust)  
- `predictor.py` loads `model.pkl` for the API

### Next modeling steps

1. Multilingual transformer (MuRIL / IndicBERT) on Hinglish digital-arrest style text.  
2. Threshold tuning on a held-out citizen-facing FPR budget.  
3. Keep `predict(text) -> {risk_score, risk_level, labels, signals, explanation}` stable.

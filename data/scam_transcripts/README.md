# Scam transcripts data (`data/scam_transcripts`)

Real, publicly available fraud-call and SMS corpora for the **scam detection** module.

## Important disclaimer

**Real transcripts of live multi-day “digital arrest” video-call scams are not publicly released** — they are active case evidence held by law enforcement / victims’ counsel.

The datasets here are **real-world fraud-call and SMS spam corpora** used as the **closest available public proxy** for scam language patterns (urgency, authority impersonation, OTP/KYC harvest, prize/lottery lures, etc.).

**Do not describe or present this folder as verbatim digital-arrest call data.**

## Sources (all real / public — no synthetic text)

| # | Dataset | Access | Labels (raw → normalized) |
| --- | --- | --- | --- |
| 1 | [Fraud Call Detection Dataset](https://www.kaggle.com/datasets/narayanyadav/fraud-call-india-dataset) (`narayanyadav/fraud-call-india-dataset`) | Kaggle API (preferred); public mirror fallback | `fraud` / `normal` → `fraud` / `normal` |
| 2 | [India Spam SMS Classification](https://www.kaggle.com/datasets/junioralive/india-spam-sms-classification) (`junioralive/india-spam-sms-classification`) | Kaggle API (preferred); [GitHub CSV](https://github.com/junioralive/india-spam-sms-classification) of the same dataset | `spam` / `ham` → `fraud` / `normal` |
| 3 | [SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) (`uciml/sms-spam-collection-dataset`) | Kaggle API or official [UCI zip](https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip) | `spam` / `ham` → `fraud` / `normal` |

## Unified schema (`combined.jsonl`)

Each line is a JSON object:

```json
{
  "id": "source:sha1prefix",
  "text": "…original message or call transcript…",
  "label": "fraud | normal",
  "source_dataset": "narayanyadav/fraud-call-india-dataset | junioralive/… | uciml/…"
}
```

## Loader

```bash
# Optional: Kaggle credentials
mkdir -p ~/.kaggle
# put kaggle.json there, or export KAGGLE_USERNAME / KAGGLE_KEY

cd data/scam_transcripts
python load.py
```

Outputs:

- `combined.jsonl` — merged, de-duplicated records  
- `class_balance.json` — counts + imbalance flag  
- `raw/` — downloaded source files  

The loader prints class balance and **flags** if majority/minority ratio exceeds `3.0`.

## License / ethics

Respect each source’s license (UCI CC BY 4.0; Kaggle dataset terms; India SMS MIT on GitHub). Use for defensive research and product prototyping only. Do not attempt to re-identify individuals.

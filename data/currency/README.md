# Currency images (`data/currency`)

Folders for Module B — **Counterfeit Currency CV Agent**.

```
data/currency/
├── genuine/       # place real ₹500 (or other) note photos here
├── counterfeit/   # synthetic counterfeit-like images from the augmenter
├── manifest.csv   # written by notebooks/augment_counterfeit.py
└── README.md
```

## Important disclaimer

**Any images under `counterfeit/` produced by `notebooks/augment_counterfeit.py`
are a synthetic proxy dataset for demo / model-pipeline purposes only.**

They are **not** real counterfeit banknote specimens. Defects are injected
programmatically (blur, broken security-thread continuity, serial distortion,
latent-image degradation) onto copies of images you place in `genuine/`.

Do **not** present these files as seized or forensic counterfeit evidence.

## How to generate the synthetic proxy set

1. Copy real, lawfully obtained note photographs into `genuine/`  
   (e.g. your own photos of ₹500 notes for research).
2. Run:

```bash
python notebooks/augment_counterfeit.py
# or with explicit paths:
python notebooks/augment_counterfeit.py \
  --genuine data/currency/genuine \
  --out data/currency/counterfeit \
  --manifest data/currency/manifest.csv
```

3. Outputs land in `counterfeit/` with a `manifest.csv` mapping each filename
   to which defect(s) were injected.

If `genuine/` is empty, the script exits with a clear message and does not
fabricate currency artwork from scratch.

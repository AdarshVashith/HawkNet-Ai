# Counterfeit currency CV — exploration notes

## Data layout

```
data/currency/
  genuine/       # real note photos you provide (e.g. ₹500)
  counterfeit/   # SYNTHETIC proxy images from augment_counterfeit.py
  manifest.csv   # filename → injected defect(s)
```

## Disclaimer

Outputs of `notebooks/augment_counterfeit.py` are a **synthetic proxy dataset
for demo purposes only** — **not** real counterfeit specimens.

## Augmentation (Prompt 3.1)

```bash
python notebooks/augment_counterfeit.py
# or with labelled DEMO canvases (not legal tender):
python notebooks/augment_counterfeit.py --make-demo-placeholders
```

| id | Effect |
| --- | --- |
| `microprint_blur` | Blur / downsample microprint-like band |
| `security_thread_break` | Gaps in vertical security-thread band |
| `serial_number_distort` | Shear / shift serial-number-like regions |
| `latent_image_remove` | Flatten latent-image-like panel |

## CV model (Prompt 3.2)

```bash
cd backend
PYTHONPATH=. python -m app.models.counterfeit.train_cv
# -> app/models/counterfeit/currency_model.pt
# -> app/models/counterfeit/metrics_cv.json
```

- Frozen **MobileNetV2** + small classification head (torchvision)
- OpenCV region explainability: `security_thread`, `microprint`, `serial_number`
- Metrics: accuracy, precision, recall + **per-defect catch rate**

Tiny demo metrics (3 genuine + 15 synthetic): accuracy/precision/recall = 1.0 on
hold-out — pipeline validation only, not forensic performance.

## API scan (Prompt 3.3)

```bash
curl -X POST http://localhost:8000/api/counterfeit/scan \
  -F "file=@data/currency/genuine/demo_note_01.png"
```

Returns `{ verdict, confidence, region_scores, recommended_action }`.
Confidence in **[0.40, 0.60]** → `uncertain` (manual review). Every scan is
hash-chained via `audit_log`.

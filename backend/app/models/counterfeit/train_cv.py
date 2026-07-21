#!/usr/bin/env python3
"""Train a lightweight currency counterfeit classifier (MobileNetV2 head).

Uses genuine/ vs counterfeit/ under data/currency/. Prefers torchvision
MobileNetV2 with a frozen base + small classification head. Falls back to a
sklearn feature model if torch is unavailable so the pipeline still trains.

Also runs the OpenCV region explainability layer and reports a per-defect-type
breakdown (which synthetic defect tags are caught vs missed).

IMPORTANT: Training images under counterfeit/ are a synthetic proxy dataset
for demo purposes — not real counterfeit specimens.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.models.counterfeit.regions import analyze_regions

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
DEFAULT_GENUINE = PROJECT_ROOT / "data" / "currency" / "genuine"
DEFAULT_COUNTERFEIT = PROJECT_ROOT / "data" / "currency" / "counterfeit"
MODEL_PATH = HERE / "currency_model.pt"
SKLEARN_MODEL_PATH = HERE / "currency_model.joblib"
METRICS_PATH = HERE / "metrics_cv.json"
MODEL_VERSION = "mobilenetv2-currency-0.1.0"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
IMG_SIZE = 224

# Uncertain band for API (Prompt 3.3): justified in predictor/API comments.
UNCERTAIN_LOW = 0.40
UNCERTAIN_HIGH = 0.60


def list_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def load_image_bgr(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Failed to read {path}")
    return img


def defect_tags_from_name(name: str) -> list[str]:
    """Parse defect tags from augmenter filenames: ``*__cf__a+b+c.png``."""
    if "__cf__" not in name:
        return []
    tag = name.split("__cf__", 1)[1]
    tag = re.sub(r"\.[^.]+$", "", tag)
    if tag in {"all", "none"}:
        return ["all"] if tag == "all" else []
    return [t for t in tag.replace("|", "+").split("+") if t]


def region_feature_vector(img: np.ndarray) -> np.ndarray:
    scores = analyze_regions(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_r = cv2.resize(gray, (64, 32))
    hist = cv2.calcHist([gray_r], [0], None, [16], [0, 256]).flatten()
    hist = hist / (hist.sum() + 1e-6)
    edges = cv2.Canny(gray_r, 50, 150)
    return np.concatenate(
        [
            np.array(
                [
                    scores.security_thread,
                    scores.microprint,
                    scores.serial_number,
                    scores.latent_panel,
                    float(edges.mean() / 255.0),
                    float(gray_r.std() / 64.0),
                ],
                dtype=np.float32,
            ),
            hist.astype(np.float32),
        ]
    )


def torch_available() -> bool:
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401

        return True
    except Exception:
        return False


def build_torch_model(num_classes: int = 2):
    import torch
    import torch.nn as nn
    from torchvision import models

    try:
        weights = models.MobileNet_V2_Weights.DEFAULT
        backbone = models.mobilenet_v2(weights=weights)
        preprocess = weights.transforms()
    except Exception:
        backbone = models.mobilenet_v2(pretrained=True)
        preprocess = None

    # Freeze base
    for p in backbone.parameters():
        p.requires_grad = False

    in_features = backbone.classifier[1].in_features
    backbone.classifier = nn.Sequential(
        nn.Dropout(p=0.2),
        nn.Linear(in_features, 64),
        nn.ReLU(inplace=True),
        nn.Linear(64, num_classes),
    )
    # Train only the head
    for p in backbone.classifier.parameters():
        p.requires_grad = True
    return backbone, preprocess


def train_torch(
    paths: list[Path],
    labels: list[int],
    epochs: int = 12,
    batch_size: int = 4,
    seed: int = 42,
) -> dict[str, Any]:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset
    from torchvision import transforms

    device = torch.device("cpu")
    model, weight_transforms = build_torch_model(2)
    model = model.to(device)

    if weight_transforms is not None:
        tfm = weight_transforms
    else:
        tfm = transforms.Compose(
            [
                transforms.ToPILImage(),
                transforms.Resize((IMG_SIZE, IMG_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ]
        )

    class NoteDS(Dataset):
        def __init__(self, items: list[tuple[Path, int]]):
            self.items = items

        def __len__(self) -> int:
            return len(self.items)

        def __getitem__(self, idx: int):
            path, y = self.items[idx]
            bgr = load_image_bgr(path)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            # weight transforms expect PIL or tensor depending on version
            try:
                from PIL import Image

                x = tfm(Image.fromarray(rgb))
            except Exception:
                x = tfm(rgb)
            return x, torch.tensor(y, dtype=torch.long)

    idx = list(range(len(paths)))
    y = np.asarray(labels)
    # Stratified split; with tiny n allow non-stratified fallback
    try:
        train_idx, test_idx = train_test_split(
            idx, test_size=0.33, random_state=seed, stratify=y
        )
    except ValueError:
        train_idx, test_idx = train_test_split(idx, test_size=0.33, random_state=seed)

    train_items = [(paths[i], labels[i]) for i in train_idx]
    test_items = [(paths[i], labels[i]) for i in test_idx]

    # Oversample minority in train for tiny genuine set
    by_label: dict[int, list[tuple[Path, int]]] = defaultdict(list)
    for it in train_items:
        by_label[it[1]].append(it)
    max_n = max(len(v) for v in by_label.values())
    balanced: list[tuple[Path, int]] = []
    rng = random.Random(seed)
    for lab, items in by_label.items():
        balanced.extend(items)
        while len([1 for x in balanced if x[1] == lab]) < max_n:
            balanced.append(rng.choice(items))

    train_loader = DataLoader(NoteDS(balanced), batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(NoteDS(test_items), batch_size=1, shuffle=False)

    opt = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-3)
    crit = nn.CrossEntropyLoss()

    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        n = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = crit(logits, yb)
            loss.backward()
            opt.step()
            total_loss += float(loss.item()) * len(yb)
            n += len(yb)
        print(f"epoch {epoch+1}/{epochs}  loss={total_loss / max(n,1):.4f}")

    model.eval()
    y_true: list[int] = []
    y_pred: list[int] = []
    y_prob: list[float] = []
    with torch.no_grad():
        for xb, yb in test_loader:
            xb = xb.to(device)
            logits = model(xb)
            prob = torch.softmax(logits, dim=1)[0, 1].item()  # P(counterfeit)
            pred = int(prob >= 0.5)
            y_true.append(int(yb.item()))
            y_pred.append(pred)
            y_prob.append(prob)

    torch.save(
        {
            "state_dict": model.state_dict(),
            "model_version": MODEL_VERSION,
            "backend": "torchvision_mobilenet_v2",
            "class_map": {"0": "genuine", "1": "counterfeit"},
            "img_size": IMG_SIZE,
        },
        MODEL_PATH,
    )
    print(f"Saved torch model -> {MODEL_PATH}")

    return {
        "backend": "torchvision_mobilenet_v2",
        "model_path": str(MODEL_PATH),
        "y_true": y_true,
        "y_pred": y_pred,
        "y_prob": y_prob,
        "test_paths": [str(paths[i]) for i in test_idx],
        "train_size": len(train_items),
        "test_size": len(test_items),
    }


def train_sklearn_fallback(
    paths: list[Path], labels: list[int], seed: int = 42
) -> dict[str, Any]:
    """Fallback when torch is not installed: region + hand features + logreg."""
    X = np.stack([region_feature_vector(load_image_bgr(p)) for p in paths])
    y = np.asarray(labels)
    try:
        X_train, X_test, y_train, y_test, p_train, p_test = train_test_split(
            X, y, paths, test_size=0.33, random_state=seed, stratify=y
        )
    except ValueError:
        X_train, X_test, y_train, y_test, p_train, p_test = train_test_split(
            X, y, paths, test_size=0.33, random_state=seed
        )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
    clf.fit(X_train_s, y_train)
    proba = clf.predict_proba(X_test_s)[:, 1]
    pred = (proba >= 0.5).astype(int)

    bundle = {
        "model": clf,
        "scaler": scaler,
        "model_version": "sklearn-region-features-0.1.0",
        "backend": "sklearn_region_logreg",
        "class_map": {"0": "genuine", "1": "counterfeit"},
    }
    joblib.dump(bundle, SKLEARN_MODEL_PATH)
    # Also write a small marker next to expected path for predictor discovery
    print(f"Saved sklearn fallback model -> {SKLEARN_MODEL_PATH}")
    return {
        "backend": "sklearn_region_logreg",
        "model_path": str(SKLEARN_MODEL_PATH),
        "y_true": y_test.tolist(),
        "y_pred": pred.tolist(),
        "y_prob": proba.tolist(),
        "test_paths": [str(p) for p in p_test],
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
    }


def per_defect_breakdown(
    paths: list[Path], labels: list[int], preds: list[int] | None = None
) -> dict[str, Any]:
    """Evaluate catch rate by synthetic defect type on counterfeit images.

    If preds is None, uses region-heuristic threshold on full image suspicion.
    """
    caught: Counter[str] = Counter()
    total: Counter[str] = Counter()
    details: list[dict[str, Any]] = []

    for i, path in enumerate(paths):
        if labels[i] != 1:
            continue
        tags = defect_tags_from_name(path.name) or ["unknown"]
        img = load_image_bgr(path)
        regions = analyze_regions(img)
        if preds is not None:
            is_caught = bool(preds[i] == 1)
        else:
            # Heuristic: any strong region suspicion
            is_caught = max(
                regions.security_thread,
                regions.microprint,
                regions.serial_number,
                regions.latent_panel,
            ) >= 0.45
        for t in tags:
            total[t] += 1
            if is_caught:
                caught[t] += 1
        details.append(
            {
                "file": path.name,
                "defects": tags,
                "caught": is_caught,
                "region_scores": regions.as_dict(),
            }
        )

    summary = {}
    for t in sorted(total):
        summary[t] = {
            "total": total[t],
            "caught": caught[t],
            "missed": total[t] - caught[t],
            "catch_rate": round(caught[t] / total[t], 4) if total[t] else None,
        }
    return {"by_defect": summary, "examples": details[:20]}


def compute_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_counterfeit": float(
            precision_score(y_true, y_pred, pos_label=1, zero_division=0)
        ),
        "recall_counterfeit": float(
            recall_score(y_true, y_pred, pos_label=1, zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "classification_report": classification_report(
            y_true,
            y_pred,
            target_names=["genuine", "counterfeit"],
            digits=4,
            zero_division=0,
        ),
    }


def collect_dataset(
    genuine_dir: Path, counterfeit_dir: Path
) -> tuple[list[Path], list[int]]:
    genuine = list_images(genuine_dir)
    counterfeit = list_images(counterfeit_dir)
    paths = genuine + counterfeit
    labels = [0] * len(genuine) + [1] * len(counterfeit)
    if not genuine or not counterfeit:
        raise RuntimeError(
            f"Need images in both folders. genuine={len(genuine)} counterfeit={len(counterfeit)}"
        )
    return paths, labels


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genuine", type=Path, default=DEFAULT_GENUINE)
    parser.add_argument("--counterfeit", type=Path, default=DEFAULT_COUNTERFEIT)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--force-sklearn",
        action="store_true",
        help="Skip torch even if installed",
    )
    args = parser.parse_args(argv)

    print(
        "NOTE: counterfeit/ images are a synthetic proxy dataset for demo purposes, "
        "not real counterfeit specimens."
    )
    paths, labels = collect_dataset(args.genuine, args.counterfeit)
    print(f"Dataset: genuine={(np.array(labels)==0).sum()}  counterfeit={(np.array(labels)==1).sum()}")

    use_torch = torch_available() and not args.force_sklearn
    if use_torch:
        print("Training torchvision MobileNetV2 (frozen base + classification head)…")
        result = train_torch(paths, labels, epochs=args.epochs, seed=args.seed)
    else:
        print("torch/torchvision not available — training sklearn region-feature fallback…")
        result = train_sklearn_fallback(paths, labels, seed=args.seed)

    metrics = compute_metrics(result["y_true"], result["y_pred"])
    print("\n=== Hold-out metrics (positive = counterfeit) ===")
    print(f"Accuracy : {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision_counterfeit']:.4f}")
    print(f"Recall   : {metrics['recall_counterfeit']:.4f}")
    print("Confusion matrix [rows=true genuine,cf | cols=pred]:")
    print(np.array(metrics["confusion_matrix"]))
    print(metrics["classification_report"])

    # Per-defect breakdown on ALL counterfeit images using trained model preds where possible
    cf_paths = [p for p, y in zip(paths, labels) if y == 1]
    # Score each counterfeit with region layer + model if available
    cf_preds: list[int] = []
    if result["backend"].startswith("torch"):
        # Load and score
        import torch
        from PIL import Image
        from torchvision import transforms

        bundle = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        model, weight_transforms = build_torch_model(2)
        model.load_state_dict(bundle["state_dict"])
        model.eval()
        if weight_transforms is not None:
            tfm = weight_transforms
        else:
            tfm = transforms.Compose(
                [
                    transforms.ToPILImage(),
                    transforms.Resize((IMG_SIZE, IMG_SIZE)),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                    ),
                ]
            )
        with torch.no_grad():
            for p in cf_paths:
                bgr = load_image_bgr(p)
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                x = tfm(Image.fromarray(rgb)).unsqueeze(0)
                prob = torch.softmax(model(x), dim=1)[0, 1].item()
                cf_preds.append(int(prob >= 0.5))
    else:
        bundle = joblib.load(SKLEARN_MODEL_PATH)
        for p in cf_paths:
            feat = region_feature_vector(load_image_bgr(p)).reshape(1, -1)
            feat = bundle["scaler"].transform(feat)
            prob = float(bundle["model"].predict_proba(feat)[0, 1])
            cf_preds.append(int(prob >= 0.5))

    defect_report = per_defect_breakdown(cf_paths, [1] * len(cf_paths), cf_preds)
    print("\n=== Per-defect-type catch rate (synthetic tags) ===")
    for defect, stats in defect_report["by_defect"].items():
        print(
            f"  {defect:30s}  caught={stats['caught']}/{stats['total']}  "
            f"missed={stats['missed']}  rate={stats['catch_rate']}"
        )

    out = {
        "model_version": MODEL_VERSION if use_torch else "sklearn-region-features-0.1.0",
        "backend": result["backend"],
        "model_path": result["model_path"],
        "train_size": result["train_size"],
        "test_size": result["test_size"],
        "metrics": {k: v for k, v in metrics.items() if k != "classification_report"},
        "classification_report": metrics["classification_report"],
        "per_defect_breakdown": defect_report["by_defect"],
        "disclaimer": (
            "Trained on synthetic proxy counterfeit images for demo — "
            "not real counterfeit specimens."
        ),
        "uncertain_band": {"low": UNCERTAIN_LOW, "high": UNCERTAIN_HIGH},
    }
    METRICS_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote metrics -> {METRICS_PATH}")
    return 0


if __name__ == "__main__":
    # Allow running as module or script
    backend_root = Path(__file__).resolve().parents[2]  # .../backend
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    raise SystemExit(main())

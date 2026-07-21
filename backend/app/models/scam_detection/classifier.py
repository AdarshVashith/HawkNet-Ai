#!/usr/bin/env python3
"""Train a scikit-learn scam-detection classifier on real public transcripts.

Data
----
Reads JSONL with schema ``{id, text, label, source_dataset}`` where
``label ∈ {fraud, normal}``. Default path:

    data/scam_transcripts/transcripts.jsonl

(falls back to ``combined.jsonl`` produced by ``data/scam_transcripts/load.py``).

Model
-----
Hand-crafted features (see ``feature_extractor.py``) + TF-IDF word n-grams,
fed into a calibrated Logistic Regression (class-weighted). GradientBoosting
is available via ``--model gb``.

Why we favor recall on the scam class
------------------------------------
Missing a real scam (false negative) can leave a citizen exposed to financial
loss, coercion, or digital-arrest social engineering. We therefore:

  * use ``class_weight="balanced"`` (or sample weights) so the minority scam
    class is not drowned out;
  * report **recall on the fraud/scam class as the primary selection metric**;
  * still **track false-positive rate / precision separately**, because
    citizen-facing false alarms erode trust and can cause alert fatigue or
    wrongful friction. Precision and FPR are printed and stored in metrics,
    but we do not optimize purely for accuracy.

Usage
-----
    cd backend
    PYTHONPATH=. python -m app.models.scam_detection.classifier

Saves ``model.pkl`` next to this file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.models.scam_detection.feature_extractor import (
    FEATURE_NAMES,
    extract_features,
    features_matrix,
)

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[4]  # digital-public-safety-platform/
DEFAULT_DATA_CANDIDATES = [
    PROJECT_ROOT / "data" / "scam_transcripts" / "transcripts.jsonl",
    PROJECT_ROOT / "data" / "scam_transcripts" / "combined.jsonl",
]
MODEL_PATH = HERE / "model.pkl"
METRICS_PATH = HERE / "metrics.json"
MODEL_VERSION = "sklearn-handcrafted+tfidf-0.1.0"


def resolve_data_path(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
    for candidate in DEFAULT_DATA_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "No transcripts JSONL found. Run data/scam_transcripts/load.py first, "
        f"or pass --data. Looked in: {DEFAULT_DATA_CANDIDATES}"
    )


def load_jsonl(path: Path) -> tuple[list[str], list[int], list[str]]:
    texts: list[str] = []
    labels: list[int] = []
    sources: list[str] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = (row.get("text") or "").strip()
            label_raw = (row.get("label") or "").strip().lower()
            if not text or label_raw not in {"fraud", "normal", "spam", "ham"}:
                continue
            # fraud/spam -> 1 (scam), normal/ham -> 0
            y = 1 if label_raw in {"fraud", "spam"} else 0
            texts.append(text)
            labels.append(y)
            sources.append(row.get("source_dataset") or "unknown")
    if not texts:
        raise RuntimeError(f"No usable rows in {path}")
    return texts, labels, sources


def build_feature_blocks(
    texts: list[str],
    tfidf: TfidfVectorizer | None = None,
    hand_scaler: StandardScaler | None = None,
    fit: bool = False,
) -> tuple[csr_matrix, TfidfVectorizer, StandardScaler]:
    hand = np.asarray(features_matrix(texts), dtype=np.float64)
    if fit or hand_scaler is None:
        hand_scaler = StandardScaler(with_mean=True)
        hand_scaled = hand_scaler.fit_transform(hand)
    else:
        hand_scaled = hand_scaler.transform(hand)

    if fit or tfidf is None:
        tfidf = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            max_features=20000,
            sublinear_tf=True,
        )
        tfidf_mat = tfidf.fit_transform(texts)
    else:
        tfidf_mat = tfidf.transform(texts)

    combined = hstack([csr_matrix(hand_scaled), tfidf_mat], format="csr")
    return combined, tfidf, hand_scaler


def make_estimator(kind: str):
    if kind == "gb":
        # Gradient boosting on dense hand features is slow with huge TF-IDF;
        # we still allow it but prefer logistic for sparse hybrid features.
        return GradientBoostingClassifier(random_state=42)
    # Default: class-weighted logistic regression — strong baseline for sparse text
    # and lets us push recall on the minority scam class via class_weight.
    base = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        solver="liblinear",
        random_state=42,
    )
    return base


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    # Positive class = scam/fraud (1)
    precision = precision_score(y_true, y_pred, pos_label=1, zero_division=0)
    recall = recall_score(y_true, y_pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_true, y_pred, pos_label=1, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "precision_scam": float(precision),
        "recall_scam": float(recall),
        "f1_scam": float(f1),
        "false_positive_rate": float(fpr),
        "confusion_matrix": {
            "labels": ["normal(0)", "scam(1)"],
            "matrix": cm.tolist(),
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
        "classification_report": classification_report(
            y_true,
            y_pred,
            target_names=["normal", "scam"],
            digits=4,
            zero_division=0,
        ),
    }


def train(
    data_path: Path,
    model_kind: str = "logreg",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    texts, labels, sources = load_jsonl(data_path)
    y = np.asarray(labels, dtype=np.int64)
    print(f"Loaded {len(texts)} transcripts from {data_path}")
    print(f"  scam(fraud)={int(y.sum())}  normal={int((y == 0).sum())}")

    idx = np.arange(len(texts))
    train_idx, test_idx = train_test_split(
        idx,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    X_train_text = [texts[i] for i in train_idx]
    X_test_text = [texts[i] for i in test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    X_train, tfidf, hand_scaler = build_feature_blocks(X_train_text, fit=True)
    X_test, _, _ = build_feature_blocks(
        X_test_text, tfidf=tfidf, hand_scaler=hand_scaler, fit=False
    )

    clf = make_estimator(model_kind)
    print(f"Training {model_kind} on {X_train.shape[0]} rows, {X_train.shape[1]} features…")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    metrics = evaluate(y_test, y_pred)

    print("\n=== Test metrics (positive class = scam/fraud) ===")
    print(f"Precision (scam): {metrics['precision_scam']:.4f}")
    print(f"Recall    (scam): {metrics['recall_scam']:.4f}   ← primary focus")
    print(f"F1        (scam): {metrics['f1_scam']:.4f}")
    print(f"False positive rate (normal→scam): {metrics['false_positive_rate']:.4f}")
    print("\nConfusion matrix [rows=true normal,scam | cols=pred normal,scam]:")
    print(np.array(metrics["confusion_matrix"]["matrix"]))
    print("\n" + metrics["classification_report"])
    print(
        "Note: We favor recall on the scam class (missed scams harm citizens) "
        "but track FPR/precision separately because citizen-facing false alarms "
        "are costly to trust."
    )

    bundle = {
        "model": clf,
        "tfidf": tfidf,
        "hand_scaler": hand_scaler,
        "feature_names": FEATURE_NAMES,
        "model_version": MODEL_VERSION,
        "model_kind": model_kind,
        "label_map": {"0": "normal", "1": "scam"},
        "metrics": {
            k: v
            for k, v in metrics.items()
            if k != "classification_report"
        },
        "train_size": int(len(train_idx)),
        "test_size": int(len(test_idx)),
        "data_path": str(data_path),
    }
    joblib.dump(bundle, MODEL_PATH)
    METRICS_PATH.write_text(
        json.dumps(
            {
                "model_version": MODEL_VERSION,
                "model_kind": model_kind,
                "data_path": str(data_path),
                "n_samples": len(texts),
                "metrics": bundle["metrics"],
                "classification_report": metrics["classification_report"],
            },
            indent=2,
        )
    )
    print(f"\nSaved model -> {MODEL_PATH}")
    print(f"Saved metrics -> {METRICS_PATH}")
    return bundle


def predict_proba_text(bundle: dict[str, Any], text: str) -> dict[str, Any]:
    """Score a single transcript with a loaded training bundle."""
    X, _, _ = build_feature_blocks(
        [text],
        tfidf=bundle["tfidf"],
        hand_scaler=bundle["hand_scaler"],
        fit=False,
    )
    clf = bundle["model"]
    if hasattr(clf, "predict_proba"):
        proba = float(clf.predict_proba(X)[0, 1])
    else:
        # decision_function fallback
        score = float(clf.decision_function(X)[0])
        proba = 1.0 / (1.0 + np.exp(-score))
    pred = int(proba >= 0.5)
    feats = extract_features(text)
    return {
        "scam_probability": proba,
        "predicted_label": "scam" if pred == 1 else "normal",
        "features": feats.as_dict(),
        "model_version": bundle.get("model_version", MODEL_VERSION),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=None, help="Path to transcripts JSONL")
    parser.add_argument(
        "--model",
        choices=["logreg", "gb"],
        default="logreg",
        help="Base estimator (default: class-weighted logistic regression)",
    )
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    data_path = resolve_data_path(args.data)
    train(
        data_path=data_path,
        model_kind=args.model,
        test_size=args.test_size,
        random_state=args.seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

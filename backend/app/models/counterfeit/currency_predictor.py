"""Currency note image predictor (MobileNetV2 + OpenCV region scores).

Combines:
  1) Transfer-learned MobileNetV2 head (or sklearn fallback) for global score
  2) Rule-based OpenCV region checks for security_thread / microprint / serial

Verdict policy
--------------
``confidence`` is P(counterfeit) from the classifier, blended with region
suspicion so explainability influences the final score.

UNCERTAIN threshold band [0.40, 0.60]:
  Citizen / teller-facing hard verdicts are costly either way — a false
  "counterfeit" can seize a legitimate note; a false "genuine" can pass a
  fake. Scores inside this band are routed to **manual review**
  (verdict='uncertain') rather than a hard call. Outside the band we emit
  genuine (<0.40) or counterfeit (>0.60).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.models.counterfeit.regions import analyze_regions

HERE = Path(__file__).resolve().parent
TORCH_MODEL = HERE / "currency_model.pt"
SKLEARN_MODEL = HERE / "currency_model.joblib"

# See module docstring — manual-review band for citizen-facing trust.
UNCERTAIN_LOW = 0.40
UNCERTAIN_HIGH = 0.60
IMG_SIZE = 224


class CurrencyCounterfeitModel:
    version = "currency-untrained-0.1.0"

    def __init__(self) -> None:
        self._backend: str | None = None
        self._torch_bundle: dict[str, Any] | None = None
        self._torch_model = None
        self._torch_tfm = None
        self._sklearn_bundle: dict[str, Any] | None = None
        self._load()

    def _load(self) -> None:
        if TORCH_MODEL.is_file():
            try:
                import torch
                from torchvision import models, transforms
                import torch.nn as nn

                bundle = torch.load(TORCH_MODEL, map_location="cpu", weights_only=False)
                try:
                    weights = models.MobileNet_V2_Weights.DEFAULT
                    backbone = models.mobilenet_v2(weights=None)
                    self._torch_tfm = weights.transforms()
                except Exception:
                    backbone = models.mobilenet_v2(pretrained=False)
                    self._torch_tfm = transforms.Compose(
                        [
                            transforms.ToPILImage(),
                            transforms.Resize((IMG_SIZE, IMG_SIZE)),
                            transforms.ToTensor(),
                            transforms.Normalize(
                                mean=[0.485, 0.456, 0.406],
                                std=[0.229, 0.224, 0.225],
                            ),
                        ]
                    )
                in_features = backbone.classifier[1].in_features
                backbone.classifier = nn.Sequential(
                    nn.Dropout(p=0.2),
                    nn.Linear(in_features, 64),
                    nn.ReLU(inplace=True),
                    nn.Linear(64, 2),
                )
                backbone.load_state_dict(bundle["state_dict"])
                backbone.eval()
                self._torch_model = backbone
                self._torch_bundle = bundle
                self._backend = "torchvision_mobilenet_v2"
                self.version = bundle.get("model_version", "mobilenetv2-currency-0.1.0")
                return
            except Exception:
                self._torch_model = None

        if SKLEARN_MODEL.is_file():
            try:
                import joblib

                self._sklearn_bundle = joblib.load(SKLEARN_MODEL)
                self._backend = "sklearn_region_logreg"
                self.version = self._sklearn_bundle.get(
                    "model_version", "sklearn-region-features-0.1.0"
                )
                return
            except Exception:
                self._sklearn_bundle = None

        self._backend = "region_heuristic"
        self.version = "currency-region-heuristic-0.1.0"

    def _decode(self, image: np.ndarray | bytes | str | Path) -> np.ndarray:
        if isinstance(image, np.ndarray):
            img = image
        elif isinstance(image, (bytes, bytearray)):
            arr = np.frombuffer(image, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        else:
            img = cv2.imread(str(image), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    def _model_p_counterfeit(self, bgr: np.ndarray) -> float:
        if self._backend == "torchvision_mobilenet_v2" and self._torch_model is not None:
            import torch
            from PIL import Image

            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            x = self._torch_tfm(Image.fromarray(rgb)).unsqueeze(0)
            with torch.no_grad():
                logits = self._torch_model(x)
                prob = float(torch.softmax(logits, dim=1)[0, 1].item())
            return prob

        if self._backend == "sklearn_region_logreg" and self._sklearn_bundle is not None:
            from app.models.counterfeit.train_cv import region_feature_vector

            feat = region_feature_vector(bgr).reshape(1, -1)
            feat = self._sklearn_bundle["scaler"].transform(feat)
            return float(self._sklearn_bundle["model"].predict_proba(feat)[0, 1])

        # Pure region heuristic
        r = analyze_regions(bgr)
        return float(
            np.clip(
                0.3 * r.security_thread
                + 0.3 * r.microprint
                + 0.25 * r.serial_number
                + 0.15 * r.latent_panel,
                0.0,
                1.0,
            )
        )

    def predict_image(self, image: np.ndarray | bytes | str | Path) -> dict[str, Any]:
        bgr = self._decode(image)
        regions = analyze_regions(bgr)
        p_model = self._model_p_counterfeit(bgr)
        region_mean = float(
            np.mean(
                [
                    regions.security_thread,
                    regions.microprint,
                    regions.serial_number,
                ]
            )
        )
        # Blend: model primary, regions as explainable contribution
        confidence = float(np.clip(0.7 * p_model + 0.3 * region_mean, 0.0, 1.0))

        # UNCERTAIN_LOW/HIGH: see module docstring — route ambiguous scores
        # to manual review rather than a hard genuine/counterfeit verdict.
        if UNCERTAIN_LOW <= confidence <= UNCERTAIN_HIGH:
            verdict = "uncertain"
            recommended_action = (
                "UNCERTAIN: confidence in the manual-review band "
                f"[{UNCERTAIN_LOW:.2f}, {UNCERTAIN_HIGH:.2f}]. "
                "Do not seize or clear the note automatically — send to a trained "
                "cashier / currency desk for physical inspection (feel, UV, tilt)."
            )
        elif confidence > UNCERTAIN_HIGH:
            verdict = "counterfeit"
            recommended_action = (
                "COUNTERFEIT SUSPECTED: quarantine the note, avoid returning it to "
                "circulation, and escalate per bank/RBI counterfeit handling SOP. "
                "Review region_scores for which security features look degraded."
            )
        else:
            verdict = "genuine"
            recommended_action = (
                "LIKELY GENUINE on image cues alone. Still follow standard cash "
                "handling checks if the transaction is high-value or the note feels off."
            )

        return {
            "verdict": verdict,
            "confidence": round(confidence, 4),
            "model_p_counterfeit": round(p_model, 4),
            "region_scores": regions.as_dict(),
            "recommended_action": recommended_action,
            "model_version": self.version,
            "backend": self._backend,
        }

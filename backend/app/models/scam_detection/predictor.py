"""Scam-detection model wrapper.

Loads ``model.pkl`` (hand-crafted features + TF-IDF + sklearn classifier)
when available; otherwise falls back to a lightweight keyword heuristic so
the API still works before training.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.models.scam_detection.feature_extractor import extract_features, SCAM_KEYWORD_PATTERNS

HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "model.pkl"

# Favor recall on the scam class: threshold slightly below 0.5 so borderline
# scam-like messages are more likely to surface for human review.
# Citizen-facing false alarms remain costly — operators should monitor FPR
# via audit logs / metrics.json rather than silently dropping the threshold.
DEFAULT_SCAM_THRESHOLD = 0.42


class ScamDetectionModel:
    version = "stub-0.1.0"

    def __init__(self) -> None:
        self._bundle: dict[str, Any] | None = None
        self._load_bundle()

    def _load_bundle(self) -> None:
        if not MODEL_PATH.is_file():
            self._bundle = None
            self.version = "stub-0.1.0"
            return
        try:
            import joblib

            self._bundle = joblib.load(MODEL_PATH)
            self.version = self._bundle.get("model_version", "sklearn-0.1.0")
        except Exception:  # noqa: BLE001 — keep API up if artifact corrupt
            self._bundle = None
            self.version = "stub-0.1.0"

    def predict(self, text: str) -> dict:
        if self._bundle is not None:
            try:
                return self._predict_sklearn(text)
            except Exception:  # noqa: BLE001 — fall back to stub on model artifact incompatibility
                return self._predict_stub(text)
        return self._predict_stub(text)

    def _risk_level(self, score: float) -> str:
        if score >= 0.75:
            return "critical"
        if score >= 0.5:
            return "high"
        if score >= 0.25:
            return "medium"
        return "low"

    def _predict_sklearn(self, text: str) -> dict:
        from app.models.scam_detection.classifier import predict_proba_text

        assert self._bundle is not None
        result = predict_proba_text(self._bundle, text)
        score = float(result["scam_probability"])
        feats = result["features"]
        signals: list[str] = []
        signals.extend(feats.get("impersonation_hits") or [])
        if feats.get("urgency_score", 0) > 0:
            signals.append(f"urgency:{feats['urgency_score']:.2f}")
        if feats.get("isolation_score", 0) > 0:
            signals.append(f"isolation:{feats['isolation_score']:.2f}")
        if feats.get("request_for_video_hold"):
            signals.append("video_hold")
        if feats.get("payment_otp_request"):
            signals.append("payment_or_otp")
        if feats.get("url_count"):
            signals.append(f"urls:{feats['url_count']}")
        # Boost score with scam keyword pattern hits for prize/lottery/click-link scams
        import re as _re
        norm_text = f" {text.lower()} "
        kw_hits = sum(1 for p in SCAM_KEYWORD_PATTERNS if _re.search(p, norm_text, flags=_re.IGNORECASE))
        if kw_hits > 0:
            kw_boost = min(0.5, kw_hits * 0.08)
            score = min(1.0, score + kw_boost)
            signals.append(f"scam_keywords:{kw_hits}")

        labels = (
            ["scam_suspected"]
            if score >= DEFAULT_SCAM_THRESHOLD
            else ["benign_or_unclear"]
        )
        explanation = (
            f"sklearn model p(scam)={score:.3f} "
            f"(impersonation={feats.get('impersonation_keyword_count', 0)}, "
            f"urgency={feats.get('urgency_score', 0):.2f}, "
            f"isolation={feats.get('isolation_score', 0):.2f}, "
            f"video_hold={bool(feats.get('request_for_video_hold'))}, "
            f"payment_otp={bool(feats.get('payment_otp_request'))}). "
            "Recall on scam class is prioritized; FPR tracked separately."
        )
        return {
            "risk_score": round(score, 3),
            "risk_level": self._risk_level(score),
            "labels": labels,
            "signals": signals,
            "explanation": explanation,
            "model_version": self.version,
        }

    def _predict_stub(self, text: str) -> dict:
        import re as _re
        feats = extract_features(text)
        norm_text = f" {text.lower()} "
        # Count scam keyword pattern hits for prize/lottery/click-link scams
        kw_hits = sum(1 for p in SCAM_KEYWORD_PATTERNS if _re.search(p, norm_text, flags=_re.IGNORECASE))
        score = min(
            1.0,
            0.12 * feats.impersonation_keyword_count
            + 0.35 * feats.urgency_score
            + 0.35 * feats.isolation_score
            + (0.25 if feats.request_for_video_hold else 0.0)
            + (0.25 if feats.payment_otp_request else 0.0)
            + 0.12 * min(feats.url_count, 3)
            + 0.08 * min(kw_hits, 5),
        )
        signals = list(feats.impersonation_hits)
        if feats.request_for_video_hold:
            signals.append("video_hold")
        if feats.payment_otp_request:
            signals.append("payment_or_otp")
        if feats.url_count:
            signals.append(f"urls:{feats.url_count}")
        if kw_hits:
            signals.append(f"scam_keywords:{kw_hits}")
        labels = ["scam_suspected"] if score >= 0.5 else ["benign_or_unclear"]
        return {
            "risk_score": round(score, 3),
            "risk_level": self._risk_level(score),
            "labels": labels,
            "signals": signals,
            "explanation": (
                f"Heuristic features: impersonation={feats.impersonation_keyword_count}, "
                f"urgency={feats.urgency_score:.2f}, isolation={feats.isolation_score:.2f}, "
                f"scam_keywords={kw_hits}, urls={feats.url_count}."
            ),
            "model_version": self.version,
        }

"""Counterfeit module models.

- ``CounterfeitModel``: listing-metadata stub (product pages / marketplace text)
- ``CurrencyCounterfeitModel``: note-image CV predictor (Prompt 3.2/3.3)
"""

from __future__ import annotations

from app.models.counterfeit.currency_predictor import CurrencyCounterfeitModel


class CounterfeitModel:
    """Stub counterfeit-goods listing model (marketplace text signals)."""

    version = "stub-0.1.0"

    def predict(
        self,
        product_name: str,
        brand: str | None = None,
        price: float | None = None,
        description: str | None = None,
    ) -> dict:
        red_flags: list[str] = []
        score = 0.1
        text = f"{product_name} {brand or ''} {description or ''}".lower()

        if any(token in text for token in ("replica", "1:1", "aaa quality", "mirror copy")):
            red_flags.append("explicit_replica_language")
            score += 0.45
        if price is not None and brand and price < 20:
            red_flags.append("price_too_low_for_brand")
            score += 0.3
        if "official" in text and "not official" in text:
            red_flags.append("contradictory_official_claim")
            score += 0.2

        score = min(1.0, score)
        authenticity = round(1.0 - score, 3)
        if score >= 0.75:
            level = "critical"
        elif score >= 0.5:
            level = "high"
        elif score >= 0.25:
            level = "medium"
        else:
            level = "low"

        return {
            "risk_score": round(score, 3),
            "risk_level": level,
            "authenticity_score": authenticity,
            "red_flags": red_flags,
            "explanation": (
                f"Found {len(red_flags)} authenticity red flag(s)."
                if red_flags
                else "No strong counterfeit signals in listing metadata."
            ),
            "model_version": self.version,
        }


__all__ = ["CounterfeitModel", "CurrencyCounterfeitModel"]

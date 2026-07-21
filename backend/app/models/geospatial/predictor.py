"""Stub geospatial risk model.

Uses a deterministic hash of coordinates to simulate hotspot density.
"""

from __future__ import annotations

import hashlib


class GeospatialModel:
    version = "stub-0.1.0"

    def predict(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 1.0,
        category: str | None = None,
    ) -> dict:
        key = f"{round(latitude, 3)}:{round(longitude, 3)}:{category or 'general'}"
        digest = hashlib.sha256(key.encode()).hexdigest()
        hotspots = int(digest[:2], 16) % 8
        score = min(1.0, hotspots / 7.0 * min(radius_km, 5) / 5 + 0.05)

        if score >= 0.75:
            level = "critical"
        elif score >= 0.5:
            level = "high"
        elif score >= 0.25:
            level = "medium"
        else:
            level = "low"

        recommendations = []
        if score >= 0.5:
            recommendations.append("Increase patrol density during peak evening hours.")
            recommendations.append("Push citizen alerts for high-risk micro-zones.")
        else:
            recommendations.append("Continue routine monitoring.")

        return {
            "risk_score": round(score, 3),
            "risk_level": level,
            "hotspots_nearby": hotspots,
            "region_label": f"cell-{digest[:6]}",
            "recommendations": recommendations,
            "explanation": (
                f"Simulated {hotspots} hotspot(s) within ~{radius_km} km "
                f"for category '{category or 'general'}'."
            ),
            "model_version": self.version,
        }

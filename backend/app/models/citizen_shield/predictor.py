"""Stub triage for citizen reports."""

from __future__ import annotations


class CitizenShieldModel:
    version = "stub-0.1.0"

    def triage(self, category: str, description: str) -> dict:
        priority = "normal"
        lowered = description.lower()
        if category in {"scam", "harassment"} or any(
            token in lowered for token in ("threat", "weapon", "emergency")
        ):
            priority = "elevated"
        return {
            "priority": priority,
            "routing_queue": f"queue-{category}",
            "model_version": self.version,
        }

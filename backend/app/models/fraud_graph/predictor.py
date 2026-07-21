"""Lightweight stub fraud-graph scorer for ad-hoc entity/edge payloads."""

from __future__ import annotations

from collections import defaultdict


class FraudGraphModel:
    version = "stub-0.1.0"

    def predict(self, entities: list[dict], edges: list[dict], seed_entity_id: str | None = None) -> dict:
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            adjacency[edge["source"]].add(edge["target"])
            adjacency[edge["target"]].add(edge["source"])

        start = seed_entity_id or (entities[0]["id"] if entities else "unknown")
        visited: set[str] = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            stack.extend(adjacency.get(node, set()) - visited)

        cluster_size = max(len(visited), 1)
        density = len(edges) / max(len(entities), 1)
        score = min(1.0, 0.1 * cluster_size + 0.2 * density)
        if score >= 0.75:
            level = "critical"
        elif score >= 0.5:
            level = "high"
        elif score >= 0.25:
            level = "medium"
        else:
            level = "low"

        suspicious = sorted(visited)[:10]
        return {
            "risk_score": round(score, 3),
            "risk_level": level,
            "cluster_size": cluster_size,
            "suspicious_entities": suspicious,
            "community_id": f"cluster-{start}",
            "explanation": (
                f"Connected component around '{start}' has size {cluster_size} "
                f"with edge density {density:.2f}."
            ),
            "model_version": self.version,
        }

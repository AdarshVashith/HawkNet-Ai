"""Test for geospatial hotspot ranking and trend classification (Prompt 5.2)."""

from __future__ import annotations


def test_geospatial_hotspots_ranking(client):
    r = client.get("/api/geospatial/hotspots")
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["status"] == "ok"
    assert "count" in body
    assert isinstance(body["hotspots"], list)
    assert len(body["hotspots"]) > 0

    hotspots = body["hotspots"]

    # Verify top ranked cities (e.g. Bengaluru / Mumbai / Delhi / Jamtara / Mewat)
    top_districts = [h["district"] for h in hotspots[:5]]
    assert any("Bengaluru" in d or "Mumbai" in d or "Delhi" in d or "Mewat" in d for d in top_districts), (
        f"Expected top high-cybercrime NCRB districts near top, got: {top_districts}"
    )

    # Check schema fields on first item
    first = hotspots[0]
    assert "district" in first
    assert "state" in first
    assert "cybercrime_count_2023" in first
    assert "yoy_change_pct" in first
    assert "trend" in first
    assert first["trend"] in {"emerging", "stable", "declining"}
    assert "priority_score" in first
    assert "framing_note" in first

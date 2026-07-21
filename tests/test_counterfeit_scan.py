"""Currency note scan API tests (genuine vs synthetic counterfeit)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENUINE = ROOT / "data" / "currency" / "genuine" / "demo_note_01.png"
COUNTERFEIT = (
    ROOT
    / "data"
    / "currency"
    / "counterfeit"
    / "demo_note_01__cf__microprint_blur+security_thread_break+serial_number_distort+latent_image_remove.png"
)


@pytest.fixture(scope="module", autouse=True)
def _require_samples():
    if not GENUINE.is_file() or not COUNTERFEIT.is_file():
        pytest.skip("currency sample images not present — run augment_counterfeit.py first")


def test_scan_genuine_not_counterfeit(client):
    with GENUINE.open("rb") as fh:
        resp = client.post(
            "/api/counterfeit/scan",
            files={"file": ("demo_note_01.png", fh, "image/png")},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["verdict"] in {"genuine", "uncertain", "counterfeit"}
    assert 0.0 <= body["confidence"] <= 1.0
    assert set(body["region_scores"]) >= {
        "security_thread",
        "microprint",
        "serial_number",
    }
    assert body["recommended_action"]
    assert body["audit_event_id"]
    # Genuine demo canvas should not hard-classify as counterfeit
    assert body["verdict"] in {"genuine", "uncertain"}, body


def test_scan_synthetic_counterfeit_flagged(client):
    with COUNTERFEIT.open("rb") as fh:
        resp = client.post(
            "/api/counterfeit/scan",
            files={
                "file": (
                    "demo_note_01__cf__all.png",
                    fh,
                    "image/png",
                )
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["verdict"] in {"genuine", "uncertain", "counterfeit"}
    # Multi-defect synthetic should be counterfeit or at least not genuine
    assert body["verdict"] in {"counterfeit", "uncertain"}, body
    assert body["confidence"] >= 0.40
    assert body["region_scores"]["security_thread"] >= 0.0
    assert body["audit_event_id"]

    # Audit chain should verify
    audit = client.get(f"/api/audit/{body['audit_event_id']}")
    assert audit.status_code == 200
    assert audit.json()["chain_verification"]["valid"] is True


def test_scan_relative_ordering(client):
    """Counterfeit sample should score >= genuine sample confidence."""
    with GENUINE.open("rb") as fh:
        g = client.post(
            "/api/counterfeit/scan",
            files={"file": ("g.png", fh, "image/png")},
        ).json()
    with COUNTERFEIT.open("rb") as fh:
        c = client.post(
            "/api/counterfeit/scan",
            files={"file": ("c.png", fh, "image/png")},
        ).json()
    assert c["confidence"] >= g["confidence"]

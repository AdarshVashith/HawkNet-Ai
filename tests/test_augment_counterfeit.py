"""Tests for synthetic counterfeit augmentation (demo proxy dataset)."""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "notebooks" / "augment_counterfeit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("augment_counterfeit", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["augment_counterfeit"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def aug():
    return _load_module()


def test_defect_injectors_change_image(aug):
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, size=(300, 600, 3), dtype=np.uint8)
    # Add a bright vertical strip to simulate a security thread
    img[:, 360:370] = 220

    out_a = aug.inject_microprint_blur(img)
    out_b = aug.inject_security_thread_break(img)
    out_c = aug.inject_serial_number_distort(img)
    out_d = aug.inject_latent_image_remove(img)

    assert out_a.shape == img.shape
    assert out_b.shape == img.shape
    assert out_c.shape == img.shape
    assert out_d.shape == img.shape
    # At least some pixels should change for each defect
    assert not np.array_equal(out_a, img)
    assert not np.array_equal(out_b, img)
    assert not np.array_equal(out_c, img)
    assert not np.array_equal(out_d, img)


def test_run_writes_manifest_and_outputs(aug, tmp_path):
    genuine = tmp_path / "genuine"
    counterfeit = tmp_path / "counterfeit"
    manifest = tmp_path / "manifest.csv"
    genuine.mkdir()
    # Create a simple genuine-like image
    img = np.full((240, 480, 3), 80, dtype=np.uint8)
    cv2.rectangle(img, (280, 20), (290, 220), (200, 180, 50), -1)
    cv2.putText(img, "DEMO123456", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.imwrite(str(genuine / "note01.png"), img)

    rc = aug.run(
        genuine_dir=genuine,
        counterfeit_dir=counterfeit,
        manifest_path=manifest,
        make_demo_placeholders=False,
        variants_per_image="all+singles",
    )
    assert rc == 0
    outputs = list(counterfeit.glob("*.png")) + list(counterfeit.glob("*.jpg"))
    # 1 all-defects + 4 singles
    assert len(outputs) == 5
    assert manifest.is_file()
    with manifest.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 5
    assert all(row["synthetic_proxy"] == "1" for row in rows)
    assert all(row["is_real_counterfeit_specimen"] == "0" for row in rows)
    assert any("microprint_blur" in row["defects"] for row in rows)
    assert any("security_thread_break" in row["defects"] for row in rows)
    assert any("serial_number_distort" in row["defects"] for row in rows)
    assert any("latent_image_remove" in row["defects"] for row in rows)


def test_empty_genuine_without_placeholders_fails(aug, tmp_path):
    rc = aug.run(
        genuine_dir=tmp_path / "empty_genuine",
        counterfeit_dir=tmp_path / "cf",
        manifest_path=tmp_path / "m.csv",
        make_demo_placeholders=False,
    )
    assert rc == 1

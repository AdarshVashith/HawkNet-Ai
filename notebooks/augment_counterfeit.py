#!/usr/bin/env python3
"""Generate synthetic 'counterfeit-like' note images for demo CV pipelines.

IMPORTANT — READ THIS BEFORE USING OUTPUTS
-----------------------------------------
This script creates a **synthetic proxy dataset for demo purposes only**.
It is **NOT** a collection of real counterfeit banknote specimens.

It takes photographs you place in ``data/currency/genuine/`` (e.g. real ₹500
note images you provide) and injects visual defects that *approximate* some
inspection cues used in counterfeit screening:

  (a) blur / degrade a microprint-like region
  (b) break continuity of a vertical security-thread band
  (c) shift / distort a serial-number-like region
  (d) remove / flatten a latent-image-like effect

Outputs are written to ``data/currency/counterfeit/`` with ``manifest.csv``
mapping each filename to which defect(s) were injected.

Do not present these images as forensic or seized counterfeit evidence.

Dependencies: OpenCV (cv2), Pillow (PIL), numpy.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
DEFAULT_GENUINE = PROJECT_ROOT / "data" / "currency" / "genuine"
DEFAULT_COUNTERFEIT = PROJECT_ROOT / "data" / "currency" / "counterfeit"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "currency" / "manifest.csv"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

# Defect ids written into the manifest
DEFECT_MICROPRINT_BLUR = "microprint_blur"
DEFECT_SECURITY_THREAD = "security_thread_break"
DEFECT_SERIAL_DISTORT = "serial_number_distort"
DEFECT_LATENT_REMOVE = "latent_image_remove"
ALL_DEFECTS = (
    DEFECT_MICROPRINT_BLUR,
    DEFECT_SECURITY_THREAD,
    DEFECT_SERIAL_DISTORT,
    DEFECT_LATENT_REMOVE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("augment_counterfeit")


def list_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )


def _to_bgr(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def _clamp_roi(
    h: int, w: int, y0: float, y1: float, x0: float, x1: float
) -> tuple[int, int, int, int]:
    ya = max(0, min(h - 1, int(h * y0)))
    yb = max(ya + 1, min(h, int(h * y1)))
    xa = max(0, min(w - 1, int(w * x0)))
    xb = max(xa + 1, min(w, int(w * x1)))
    return ya, yb, xa, xb


# ---------------------------------------------------------------------------
# Defect injectors (region heuristics — notes vary by photo framing)
# ---------------------------------------------------------------------------

def inject_microprint_blur(img: np.ndarray) -> np.ndarray:
    """(a) Blur / degrade a microprint-like band (lower-central strip)."""
    out = img.copy()
    h, w = out.shape[:2]
    y0, y1, x0, x1 = _clamp_roi(h, w, 0.55, 0.78, 0.12, 0.88)
    roi = out[y0:y1, x0:x1]
    # Heavy Gaussian blur + slight down/up sample to kill fine stroke detail
    blurred = cv2.GaussianBlur(roi, (0, 0), sigmaX=3.5, sigmaY=3.5)
    small = cv2.resize(blurred, (max(1, (x1 - x0) // 4), max(1, (y1 - y0) // 4)), interpolation=cv2.INTER_AREA)
    degraded = cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)
    # Mild JPEG-like blockiness via re-encode of the ROI
    ok, enc = cv2.imencode(".jpg", degraded, [int(cv2.IMWRITE_JPEG_QUALITY), 25])
    if ok:
        degraded = cv2.imdecode(enc, cv2.IMREAD_COLOR)
        if degraded is not None and degraded.shape[:2] == (y1 - y0, x1 - x0):
            out[y0:y1, x0:x1] = degraded
        else:
            out[y0:y1, x0:x1] = cv2.resize(degraded, (x1 - x0, y1 - y0)) if degraded is not None else blurred
    else:
        out[y0:y1, x0:x1] = blurred
    return out


def inject_security_thread_break(img: np.ndarray) -> np.ndarray:
    """(b) Break continuity of a vertical security-thread-like band."""
    out = img.copy()
    h, w = out.shape[:2]
    # Thread often near mid-right third on Indian notes; use a thin vertical strip
    x_center = int(w * 0.62)
    half = max(2, int(w * 0.012))
    x0, x1 = max(0, x_center - half), min(w, x_center + half)

    # Paint intermittent gaps along the strip using local background averages
    rng = np.random.default_rng(abs(hash((h, w, "thread"))) % (2**32))
    gap_h = max(8, h // 18)
    y = int(h * 0.12)
    while y < int(h * 0.88):
        if rng.random() < 0.55:
            y1 = min(h, y + gap_h)
            # Sample background just left of the thread
            bg_x0 = max(0, x0 - half * 4)
            bg_x1 = max(bg_x0 + 1, x0 - 1)
            bg = out[y:y1, bg_x0:bg_x1]
            if bg.size:
                fill = np.median(bg.reshape(-1, bg.shape[-1]), axis=0).astype(np.uint8)
            else:
                fill = np.array([180, 180, 180], dtype=np.uint8)
            out[y:y1, x0:x1] = fill
            # Soften edges of the gap
            band = out[max(0, y - 2) : min(h, y1 + 2), max(0, x0 - 3) : min(w, x1 + 3)]
            out[max(0, y - 2) : min(h, y1 + 2), max(0, x0 - 3) : min(w, x1 + 3)] = cv2.GaussianBlur(
                band, (5, 5), 0
            )
        y += gap_h + int(gap_h * 0.4)
    return out


def inject_serial_number_distort(img: np.ndarray) -> np.ndarray:
    """(c) Shift / distort a serial-number-like corner region (font warping)."""
    out = img.copy()
    h, w = out.shape[:2]
    # Upper-left serial-ish region (common placement); also touch lower-right lightly
    regions = [
        _clamp_roi(h, w, 0.06, 0.22, 0.05, 0.38),
        _clamp_roi(h, w, 0.78, 0.94, 0.58, 0.95),
    ]
    for y0, y1, x0, x1 in regions:
        roi = out[y0:y1, x0:x1].copy()
        rh, rw = roi.shape[:2]
        if rh < 8 or rw < 8:
            continue
        # Horizontal shear + slight vertical wave on the serial band
        src = np.float32([[0, 0], [rw - 1, 0], [0, rh - 1], [rw - 1, rh - 1]])
        shear = rw * 0.08
        dst = np.float32(
            [
                [shear, 0],
                [rw - 1, rh * 0.05],
                [0, rh - 1],
                [rw - 1 - shear, rh - 1 - rh * 0.04],
            ]
        )
        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(
            roi,
            M,
            (rw, rh),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )
        # Local contrast boost then slight blur → "wrong font / ink bleed" look
        pil = Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
        pil = ImageEnhance.Contrast(pil).enhance(1.35)
        pil = pil.filter(ImageFilter.UnsharpMask(radius=1.2, percent=140, threshold=2))
        warped = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        # Small integer pixel shift
        shift = max(1, rw // 40)
        M_shift = np.float32([[1, 0, shift], [0, 1, -shift // 2]])
        warped = cv2.warpAffine(
            warped, M_shift, (rw, rh), borderMode=cv2.BORDER_REFLECT_101
        )
        out[y0:y1, x0:x1] = warped
    return out


def inject_latent_image_remove(img: np.ndarray) -> np.ndarray:
    """(d) Flatten / remove a latent-image-like effect (mid-right panel).

    Latent images rely on fine directional relief. We approximate removal by
    equalizing local contrast and applying a directional motion blur so the
    angle-dependent effect disappears in a still photograph.
    """
    out = img.copy()
    h, w = out.shape[:2]
    y0, y1, x0, x1 = _clamp_roi(h, w, 0.28, 0.62, 0.68, 0.92)
    roi = out[y0:y1, x0:x1]
    # CLAHE on L channel to flatten subtle relief, then anisotropic blur
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(4, 4))
    l2 = clahe.apply(l)
    # Strong horizontal motion blur kills vertical latent ridges
    k = max(5, (x1 - x0) // 12 | 1)
    kernel = np.zeros((1, k), dtype=np.float32)
    kernel[0, :] = 1.0 / k
    l2 = cv2.filter2D(l2, -1, kernel)
    l2 = cv2.GaussianBlur(l2, (3, 3), 0)
    merged = cv2.merge([l2, a, b])
    flat = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    # Blend heavily toward flattened version
    out[y0:y1, x0:x1] = cv2.addWeighted(roi, 0.15, flat, 0.85, 0)
    return out


DEFECT_FNS = {
    DEFECT_MICROPRINT_BLUR: inject_microprint_blur,
    DEFECT_SECURITY_THREAD: inject_security_thread_break,
    DEFECT_SERIAL_DISTORT: inject_serial_number_distort,
    DEFECT_LATENT_REMOVE: inject_latent_image_remove,
}


def apply_defects(img: np.ndarray, defects: Iterable[str]) -> np.ndarray:
    out = img
    for name in defects:
        out = DEFECT_FNS[name](out)
    return out


def make_placeholder_genuine(path: Path, seed: int = 0) -> None:
    """Optional helper: draw a clearly-labelled FAKE DEMO note card.

    Not a real banknote. Only used when ``--make-demo-placeholders`` is set so
    the pipeline can be exercised without user photos.
    """
    rng = np.random.default_rng(seed)
    w, h = 1000, 450
    img = Image.new("RGB", (w, h), (40, 90, 70))
    draw = ImageDraw.Draw(img)
    # Decorative bands
    for i in range(0, h, 12):
        shade = 40 + int(20 * np.sin(i / 18))
        draw.rectangle([0, i, w, i + 6], fill=(shade, 100 + shade // 2, 80))
    # Microprint-like line
    for x in range(80, w - 80, 7):
        draw.line([(x, int(h * 0.62)), (x + 4, int(h * 0.72))], fill=(200, 220, 200), width=1)
    # Security thread
    tx = int(w * 0.62)
    draw.rectangle([tx - 4, 40, tx + 4, h - 40], fill=(220, 200, 80))
    # Serial-like text
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
        font_sm = ImageFont.truetype("DejaVuSans.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
        font_sm = font
    serial = f"DEMO{seed:02d}{rng.integers(100000, 999999)}"
    draw.text((50, 40), serial, fill=(20, 20, 20), font=font)
    draw.text((w - 280, h - 70), serial[::-1], fill=(20, 20, 20), font=font)
    # Latent-ish panel
    draw.rectangle([int(w * 0.72), int(h * 0.3), int(w * 0.9), int(h * 0.6)], outline=(230, 230, 200), width=2)
    draw.text((int(w * 0.74), int(h * 0.4)), "LATENT", fill=(210, 210, 180), font=font_sm)
    draw.text((60, h // 2 - 20), "₹500  DEMO ONLY — NOT LEGAL TENDER", fill=(240, 240, 200), font=font)
    draw.text((60, h // 2 + 20), "Synthetic canvas for augmentation tests", fill=(220, 220, 180), font=font_sm)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def process_one(
    src: Path,
    out_dir: Path,
    defects: list[str],
) -> dict:
    bgr = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if bgr is None:
        # Fallback via PIL for odd encodings
        pil = Image.open(src).convert("RGB")
        bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    bgr = _to_bgr(bgr)
    out_img = apply_defects(bgr, defects)

    defect_tag = "+".join(defects) if defects else "none"
    out_name = f"{src.stem}__cf__{defect_tag}{src.suffix.lower() or '.jpg'}"
    # sanitize overly long names
    if len(out_name) > 180:
        out_name = f"{src.stem}__cf__all{src.suffix.lower() or '.jpg'}"
    out_path = out_dir / out_name
    # Prefer PNG to avoid extra compression artifacts on top of injected ones
    if out_path.suffix.lower() in {".jpg", ".jpeg"}:
        cv2.imwrite(str(out_path), out_img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    else:
        if out_path.suffix.lower() not in IMAGE_EXTS:
            out_path = out_path.with_suffix(".png")
        cv2.imwrite(str(out_path), out_img)

    return {
        "source_filename": src.name,
        "output_filename": out_path.name,
        "defects": "|".join(defects),
        "defect_microprint_blur": int(DEFECT_MICROPRINT_BLUR in defects),
        "defect_security_thread_break": int(DEFECT_SECURITY_THREAD in defects),
        "defect_serial_number_distort": int(DEFECT_SERIAL_DISTORT in defects),
        "defect_latent_image_remove": int(DEFECT_LATENT_REMOVE in defects),
        "synthetic_proxy": 1,
        "is_real_counterfeit_specimen": 0,
        "notes": "Synthetic proxy for demo — not a real counterfeit specimen",
    }


def run(
    genuine_dir: Path,
    counterfeit_dir: Path,
    manifest_path: Path,
    make_demo_placeholders: bool = False,
    variants_per_image: str = "all+singles",
) -> int:
    log.warning(
        "SYNTHETIC PROXY DATASET ONLY — outputs are NOT real counterfeit specimens. "
        "Defects are programmatically injected for demo / CV pipeline purposes."
    )

    genuine_dir.mkdir(parents=True, exist_ok=True)
    counterfeit_dir.mkdir(parents=True, exist_ok=True)

    images = list_images(genuine_dir)
    if not images and make_demo_placeholders:
        log.info("No genuine images found; creating labelled DEMO placeholder canvases (--make-demo-placeholders).")
        for i in range(3):
            make_placeholder_genuine(genuine_dir / f"demo_note_{i+1:02d}.png", seed=i + 1)
        images = list_images(genuine_dir)

    if not images:
        log.error(
            "No images in %s. Place real ₹500 (or other) note photos in genuine/ "
            "and re-run. Refusing to invent currency artwork without --make-demo-placeholders.",
            genuine_dir,
        )
        return 1

    # Build defect combinations
    combos: list[list[str]] = []
    if variants_per_image in {"all", "all+singles"}:
        combos.append(list(ALL_DEFECTS))
    if variants_per_image in {"singles", "all+singles"}:
        for d in ALL_DEFECTS:
            combos.append([d])
    if not combos:
        combos = [list(ALL_DEFECTS)]

    rows: list[dict] = []
    for src in images:
        log.info("Processing genuine image: %s", src.name)
        for defects in combos:
            row = process_one(src, counterfeit_dir, defects)
            rows.append(row)
            log.info(
                "  -> %s  defects=[%s]  [synthetic proxy]",
                row["output_filename"],
                row["defects"],
            )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_filename",
        "output_filename",
        "defects",
        "defect_microprint_blur",
        "defect_security_thread_break",
        "defect_serial_number_distort",
        "defect_latent_image_remove",
        "synthetic_proxy",
        "is_real_counterfeit_specimen",
        "notes",
    ]
    with manifest_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d synthetic counterfeit-like images -> %s", len(rows), counterfeit_dir)
    log.info("Wrote manifest -> %s", manifest_path)
    log.warning(
        "Reminder: this is a synthetic proxy dataset for demo purposes, "
        "not real counterfeit specimens."
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--genuine", type=Path, default=DEFAULT_GENUINE, help="Folder of genuine note images")
    p.add_argument("--out", type=Path, default=DEFAULT_COUNTERFEIT, help="Output folder for synthetic counterfeits")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Manifest CSV path")
    p.add_argument(
        "--variants",
        choices=["all", "singles", "all+singles"],
        default="all+singles",
        help="Which defect combinations to generate per genuine image",
    )
    p.add_argument(
        "--make-demo-placeholders",
        action="store_true",
        help="If genuine/ is empty, create clearly labelled DEMO canvases (not real notes)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        genuine_dir=args.genuine,
        counterfeit_dir=args.out,
        manifest_path=args.manifest,
        make_demo_placeholders=args.make_demo_placeholders,
        variants_per_image=args.variants,
    )


if __name__ == "__main__":
    raise SystemExit(main())

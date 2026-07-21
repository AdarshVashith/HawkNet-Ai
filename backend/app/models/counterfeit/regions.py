"""Rule-based explainability for currency note regions.

Crops security-thread, microprint, and serial-number regions using the same
relative ROIs as the synthetic augmenter, then scores each region with OpenCV
edge/contour heuristics so the API can return per-region contributions — not
a single opaque score.

Higher region score => more *suspicious* (counterfeit-like) for that region.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import cv2
import numpy as np


@dataclass
class RegionScores:
    security_thread: float
    microprint: float
    serial_number: float
    latent_panel: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "security_thread": round(float(self.security_thread), 4),
            "microprint": round(float(self.microprint), 4),
            "serial_number": round(float(self.serial_number), 4),
        }

    def full_dict(self) -> dict[str, float]:
        d = self.as_dict()
        d["latent_panel"] = round(float(self.latent_panel), 4)
        return d


def _clamp_roi(
    h: int, w: int, y0: float, y1: float, x0: float, x1: float
) -> tuple[int, int, int, int]:
    ya = max(0, min(h - 1, int(h * y0)))
    yb = max(ya + 1, min(h, int(h * y1)))
    xa = max(0, min(w - 1, int(w * x0)))
    xb = max(xa + 1, min(w, int(w * x1)))
    return ya, yb, xa, xb


def crop_region(img: np.ndarray, y0: float, y1: float, x0: float, x1: float) -> np.ndarray:
    h, w = img.shape[:2]
    ya, yb, xa, xb = _clamp_roi(h, w, y0, y1, x0, x1)
    return img[ya:yb, xa:xb]


def _to_bgr(img: np.ndarray) -> np.ndarray:
    if img is None:
        raise ValueError("image is None")
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def _edge_density(gray: np.ndarray) -> float:
    if gray.size == 0:
        return 0.0
    edges = cv2.Canny(gray, 60, 160)
    return float(edges.mean() / 255.0)


def _contour_stats(gray: np.ndarray) -> dict[str, float]:
    if gray.size == 0:
        return {"count": 0.0, "mean_area": 0.0, "max_area": 0.0}
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return {"count": 0.0, "mean_area": 0.0, "max_area": 0.0}
    areas = [float(cv2.contourArea(c)) for c in contours]
    return {
        "count": float(len(contours)),
        "mean_area": float(np.mean(areas)),
        "max_area": float(np.max(areas)),
    }


def score_security_thread(img: np.ndarray) -> float:
    """Suspicious if vertical thread continuity is broken / weak.

    Uses a thin vertical mid-right strip (matches augmenter ROI). High score
    when edge energy is patchy (large gaps) rather than a continuous band.
    """
    bgr = _to_bgr(img)
    h, w = bgr.shape[:2]
    strip = crop_region(bgr, 0.10, 0.90, 0.58, 0.66)
    gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
    # Vertical Sobel should be strong on a continuous thread
    sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    col_energy = np.abs(sobelx).mean(axis=1)
    if col_energy.size < 4:
        return 0.5
    # Continuity: fraction of rows with energy above median*0.5
    thr = max(float(np.median(col_energy)) * 0.5, 1.0)
    continuous = float((col_energy > thr).mean())
    # Gapiness: std of binned energies
    bins = np.array_split(col_energy, 12)
    bin_means = np.array([b.mean() if len(b) else 0.0 for b in bins])
    gapiness = float(np.std(bin_means) / (np.mean(bin_means) + 1e-6))
    # Low continuity + high gapiness => suspicious
    suspicion = (1.0 - continuous) * 0.55 + min(gapiness / 2.0, 1.0) * 0.45
    return float(np.clip(suspicion, 0.0, 1.0))


def score_microprint(img: np.ndarray) -> float:
    """Suspicious if microprint band lacks fine edge density (blurred)."""
    bgr = _to_bgr(img)
    roi = crop_region(bgr, 0.55, 0.78, 0.12, 0.88)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    dens = _edge_density(gray)
    # High-frequency energy via Laplacian variance
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # Normalize roughly: sharp microprint dens~0.05-0.2, lap_var high
    dens_score = 1.0 - float(np.clip(dens / 0.12, 0.0, 1.0))
    lap_score = 1.0 - float(np.clip(lap_var / 200.0, 0.0, 1.0))
    return float(np.clip(0.55 * dens_score + 0.45 * lap_score, 0.0, 1.0))


def score_serial_number(img: np.ndarray) -> float:
    """Suspicious if serial-like corner has warped / sparse contours."""
    bgr = _to_bgr(img)
    roi = crop_region(bgr, 0.06, 0.22, 0.05, 0.38)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    stats = _contour_stats(gray)
    dens = _edge_density(gray)
    # Distortion tends to smear glyphs: fewer clean contours, lower density
    count_score = 1.0 - float(np.clip(stats["count"] / 40.0, 0.0, 1.0))
    dens_score = 1.0 - float(np.clip(dens / 0.15, 0.0, 1.0))
    # Also check aspect skew via moments
    m = cv2.moments(gray)
    mu11 = m.get("mu11", 0.0)
    mu20 = m.get("mu20", 1.0) + 1e-6
    skew = abs(mu11 / mu20)
    skew_score = float(np.clip(skew * 5.0, 0.0, 1.0))
    return float(np.clip(0.4 * dens_score + 0.35 * count_score + 0.25 * skew_score, 0.0, 1.0))


def score_latent_panel(img: np.ndarray) -> float:
    bgr = _to_bgr(img)
    roi = crop_region(bgr, 0.28, 0.62, 0.68, 0.92)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    dens = _edge_density(gray)
    # Flat latent panel after removal has low edge density / low contrast
    contrast = float(gray.std() / 64.0)
    return float(np.clip((1.0 - dens / 0.1) * 0.5 + (1.0 - min(contrast, 1.0)) * 0.5, 0.0, 1.0))


def analyze_regions(img: np.ndarray) -> RegionScores:
    """Return per-region suspicion scores in [0, 1]."""
    bgr = _to_bgr(img)
    return RegionScores(
        security_thread=score_security_thread(bgr),
        microprint=score_microprint(bgr),
        serial_number=score_serial_number(bgr),
        latent_panel=score_latent_panel(bgr),
    )


def analyze_regions_from_path(path: str | bytes) -> RegionScores:
    if isinstance(path, (bytes, bytearray)):
        arr = np.frombuffer(path, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    else:
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Could not read image: {path!r}")
    return analyze_regions(img)


def region_details(img: np.ndarray) -> dict[str, Any]:
    scores = analyze_regions(img)
    return {
        "scores": scores.full_dict(),
        "rois": {
            "security_thread": {"y0": 0.10, "y1": 0.90, "x0": 0.58, "x1": 0.66},
            "microprint": {"y0": 0.55, "y1": 0.78, "x0": 0.12, "x1": 0.88},
            "serial_number": {"y0": 0.06, "y1": 0.22, "x0": 0.05, "x1": 0.38},
            "latent_panel": {"y0": 0.28, "y1": 0.62, "x0": 0.68, "x1": 0.92},
        },
        "method": "opencv_edge_contour_heuristics",
    }

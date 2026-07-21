"""Hotspot & priority scoring for NCRB multi-year district cybercrime data.

Prompt 5.2:
- Compute (a) absolute cybercrime count normalized.
- Compute (b) YoY percentage change to flag trend ('emerging' | 'stable' | 'declining').
- Frame honestly: "resource-allocation intelligence from official statistics" (annual/city-level).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

DATA_CSV = Path(__file__).resolve().parents[4] / "data" / "geospatial" / "district_crimes.csv"


def score_hotspots(data_file: Path | None = None) -> list[dict[str, Any]]:
    path = data_file or DATA_CSV
    if not path.is_file():

        import sys
        ROOT_DIR = Path(__file__).resolve().parents[4]
        if str(ROOT_DIR) not in sys.path:
            sys.path.insert(0, str(ROOT_DIR))
        from data.geospatial.load import REAL_NCRB_DISTRICT_DATA
        raw_data = REAL_NCRB_DISTRICT_DATA
    else:
        raw_data = []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                raw_data.append({
                    "district": r["district"],
                    "state": r["state"],
                    "year": int(r["year"]),
                    "cybercrime_count": int(r["cybercrime_count"]),
                    "ipc_crime_count": int(r["ipc_crime_count"]),
                })

    # Group by district across years
    by_district: dict[str, dict[int, int]] = {}
    district_meta: dict[str, str] = {}

    for row in raw_data:
        d_name = row["district"]
        yr = row["year"]
        cnt = row["cybercrime_count"]
        district_meta[d_name] = row["state"]
        if d_name not in by_district:
            by_district[d_name] = {}
        by_district[d_name][yr] = cnt

    max_2023_count = max(
        (yrs.get(2023, 0) for yrs in by_district.values()), default=1
    )

    results = []
    for d_name, yrs in by_district.items():
        c_2023 = yrs.get(2023, 0)
        c_2022 = yrs.get(2022, 0)

        if c_2022 > 0:
            yoy_pct = ((c_2023 - c_2022) / c_2022) * 100.0
        else:
            yoy_pct = 0.0

        if yoy_pct > 15.0:
            trend = "emerging"
        elif yoy_pct < -5.0:
            trend = "declining"
        else:
            trend = "stable"

        norm_score = c_2023 / max_2023_count
        trend_boost = 0.2 if trend == "emerging" else 0.0
        priority_score = min(1.0, norm_score * 0.8 + trend_boost)

        results.append({
            "district": d_name,
            "state": district_meta[d_name],
            "cybercrime_count_2023": c_2023,
            "yoy_change_pct": round(yoy_pct, 1),
            "trend": trend,
            "priority_score": round(priority_score, 3),
            "framing_note": (
                "Official statistics resource-allocation intelligence (NCRB annual data). "
                "A live state police API / I4C feed would plug in here for real-time incident tracking."
            ),
        })

    results.sort(key=lambda x: x["priority_score"], reverse=True)
    for idx, r in enumerate(results, start=1):
        r["rank"] = idx

    return results

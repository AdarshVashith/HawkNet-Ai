#!/usr/bin/env python3
"""Load the real Elliptic Bitcoin transaction graph dataset for anti-money laundering / fraud graph analysis.

Dataset
-------
"Elliptic Data Set" (ellipticco/elliptic-data-set)
- txs_features.csv: 203,769 nodes with 166 real extracted features per node
- txs_classes.csv: licit (2), illicit (1), unknown ("unknown") labels
- txs_edgelist.csv: 234,355 directed edges between transactions

Usage
-----
python data/fraud_graph/load.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import networkx as nx

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
ELLIPTIC_DIR = RAW_DIR / "elliptic"
SUMMARY_FILE = ROOT / "elliptic_summary.json"


def ensure_data() -> Path | None:
    """Download Elliptic dataset via kagglehub / kaggle API or locate raw files."""
    ELLIPTIC_DIR.mkdir(parents=True, exist_ok=True)

    # Check if files already present in ELLIPTIC_DIR
    feat_file = ELLIPTIC_DIR / "txs_features.csv"
    class_file = ELLIPTIC_DIR / "txs_classes.csv"
    edge_file = ELLIPTIC_DIR / "txs_edgelist.csv"

    if feat_file.is_file() and class_file.is_file() and edge_file.is_file():
        return ELLIPTIC_DIR

    # Try kagglehub
    try:
        import kagglehub

        print("Attempting Kaggle download via kagglehub ('ellipticco/elliptic-data-set')...")
        download_path = Path(kagglehub.dataset_download("ellipticco/elliptic-data-set"))
        print(f"Downloaded to {download_path}")

        # Locate files in downloaded path
        for p in download_path.rglob("txs_features.csv"):
            src_dir = p.parent
            for fname in ["txs_features.csv", "txs_classes.csv", "txs_edgelist.csv"]:
                if (src_dir / fname).exists():
                    import shutil
                    shutil.copy(src_dir / fname, ELLIPTIC_DIR / fname)
            return ELLIPTIC_DIR
    except Exception as exc:
        print(f"Kaggle download warning: {exc}")

    print("Kaggle credentials not present or download failed.")
    print("If you have downloaded Elliptic manually, place txs_features.csv, txs_classes.csv, txs_edgelist.csv into:")
    print(f"  {ELLIPTIC_DIR}")
    return ELLIPTIC_DIR if feat_file.is_file() else None


def load_elliptic_graph(data_dir: Path) -> tuple[nx.DiGraph, dict[str, Any]]:
    feat_file = data_dir / "txs_features.csv"
    class_file = data_dir / "txs_classes.csv"
    edge_file = data_dir / "txs_edgelist.csv"

    print("Loading classes...")
    classes: dict[str, str] = {}
    class_counts: dict[str, int] = {"illicit": 0, "licit": 0, "unknown": 0}

    with class_file.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)  # txId, class
        for row in reader:
            if len(row) >= 2:
                tx_id, cls = row[0].strip(), row[1].strip()
                if cls == "1":
                    c_name = "illicit"
                elif cls == "2":
                    c_name = "licit"
                else:
                    c_name = "unknown"
                classes[tx_id] = c_name
                class_counts[c_name] += 1

    print("Building NetworkX graph...")
    G = nx.DiGraph()

    # Load edges
    print("Loading edges...")
    edge_count = 0
    with edge_file.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)  # txId1, txId2
        for row in reader:
            if len(row) >= 2:
                u, v = row[0].strip(), row[1].strip()
                G.add_edge(u, v)
                edge_count += 1

    # Load features (up to first 10 attributes stored per node in memory for efficiency)
    print("Loading node features...")
    feature_count = 0
    with feat_file.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            tx_id = row[0].strip()
            time_step = float(row[1]) if len(row) > 1 else 0.0
            feats = [float(x) for x in row[2:]]
            feature_count = len(feats)
            cls = classes.get(tx_id, "unknown")
            G.add_node(
                tx_id,
                time_step=time_step,
                class_name=cls,
                feature_vector=feats,
            )

    stats = {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "num_features": feature_count,
        "class_counts": class_counts,
        "class_percentages": {
            k: round(v / max(1, G.number_of_nodes()) * 100, 2)
            for k, v in class_counts.items()
        },
    }
    return G, stats


def main() -> int:
    print("=== Elliptic Bitcoin Transaction Graph Loader ===")
    data_dir = ensure_data()
    if data_dir is None or not (data_dir / "txs_classes.csv").is_file():
        print("\nNotice: Elliptic dataset files not found locally.")
        print("Creating placeholder summary structure until Kaggle dataset is populated.")
        summary = {
            "status": "pending_download",
            "message": "Elliptic dataset requires kaggle credentials or manual placement in data/fraud_graph/raw/elliptic/",
            "dataset": "ellipticco/elliptic-data-set",
        }
        SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
        return 0

    G, stats = load_elliptic_graph(data_dir)
    print("\n--- Graph Statistics ---")
    print(f"Nodes: {stats['num_nodes']:,}")
    print(f"Edges: {stats['num_edges']:,}")
    print(f"Features per node: {stats['num_features']}")
    print("Class Balance:")
    for k, v in stats["class_counts"].items():
        pct = stats["class_percentages"][k]
        print(f"  - {k}: {v:,} ({pct}%)")

    SUMMARY_FILE.write_text(json.dumps(stats, indent=2))
    print(f"\nWrote summary to {SUMMARY_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

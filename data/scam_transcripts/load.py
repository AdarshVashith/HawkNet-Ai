#!/usr/bin/env python3
"""Load real, publicly available scam / fraud text corpora into a unified schema.

NOTE (important — do not misrepresent this data):
Real transcripts of live multi-day "digital arrest" video-call scams are NOT
publicly released (they are active case evidence). The three corpora below are
real fraud-call / SMS spam datasets used as the closest available real-world
proxy for scam language patterns. This is NOT verbatim digital-arrest call data.

Sources (all real, public; no synthetic generation):
  1) Kaggle: narayanyadav/fraud-call-india-dataset
     — real fraud vs normal phone-call transcripts (India), labels fraud/normal
  2) Kaggle: junioralive/india-spam-sms-classification
     — real Indian SMS labeled spam/ham
  3) UCI / Kaggle: uciml/sms-spam-collection-dataset
     — classic real-world SMS spam/ham collection

Prefer Kaggle API (kaggle / kagglehub) when credentials exist in:
  - ~/.kaggle/kaggle.json  OR
  - env KAGGLE_USERNAME + KAGGLE_KEY

If Kaggle auth is unavailable, fall back to the same real public mirrors:
  - Fraud-call corpus redistribution used with the Kaggle fraud-call dataset
  - GitHub release of the India SMS spam collection (same as Kaggle junioralive)
  - Official UCI SMS Spam Collection zip
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
OUT_JSONL = ROOT / "combined.jsonl"
OUT_STATS = ROOT / "class_balance.json"

# Public mirrors of the same real datasets (used only when Kaggle API is unavailable).
UCI_SMS_ZIP = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
INDIA_SMS_CSV = (
    "https://raw.githubusercontent.com/junioralive/india-spam-sms-classification/"
    "main/dataset/spam_ham_india.csv"
)
# Same labeled fraud/normal call-transcript corpus distributed with the
# Narayan Yadav Fraud Call Detection Dataset / community redistributions.
FRAUD_CALL_TXT = (
    "https://raw.githubusercontent.com/harshvardhansgupta/Fraud_Call_Detection/"
    "main/main_dataset_fcd.txt"
)

KAGGLE_DATASETS = {
    "fraud_call_india": "narayanyadav/fraud-call-india-dataset",
    "india_spam_sms": "junioralive/india-spam-sms-classification",
    "uci_sms_spam": "uciml/sms-spam-collection-dataset",
}

IMBALANCE_RATIO_FLAG = 3.0  # flag if majority/minority > this


def _http_get(url: str, timeout: int = 120) -> bytes:
    req = Request(url, headers={"User-Agent": "HawkNet-Ai/0.1"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed public URLs
        return resp.read()


def _ensure_kaggle_config() -> bool:
    """Return True if Kaggle credentials are available (file or env)."""
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_json = kaggle_dir / "kaggle.json"
    if kaggle_json.is_file():
        return True
    user = os.environ.get("KAGGLE_USERNAME")
    key = os.environ.get("KAGGLE_KEY")
    if user and key:
        kaggle_dir.mkdir(parents=True, exist_ok=True)
        kaggle_json.write_text(json.dumps({"username": user, "key": key}))
        kaggle_json.chmod(0o600)
        return True
    return False


def _download_kaggle_dataset(slug: str, dest: Path) -> Path | None:
    """Download a Kaggle dataset into dest; return the directory or None on failure."""
    dest.mkdir(parents=True, exist_ok=True)
    # Prefer kagglehub (returns cached path)
    try:
        import kagglehub  # type: ignore

        path = Path(kagglehub.dataset_download(slug))
        print(f"  [kagglehub] {slug} -> {path}")
        return path
    except Exception as exc:  # noqa: BLE001
        print(f"  [kagglehub] failed for {slug}: {exc}")

    # Fallback: kaggle CLI API
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi  # type: ignore

        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(slug, path=str(dest), unzip=True, quiet=False)
        print(f"  [kaggle-api] {slug} -> {dest}")
        return dest
    except Exception as exc:  # noqa: BLE001
        print(f"  [kaggle-api] failed for {slug}: {exc}")
        return None


def _normalize_label(raw: str) -> str | None:
    """Map dataset-specific labels to {fraud, normal}."""
    v = (raw or "").strip().lower()
    if v in {"fraud", "scam", "spam", "1", "yes", "true", "phishing"}:
        return "fraud"
    if v in {"normal", "ham", "legit", "legitimate", "0", "no", "false", "not_spam"}:
        return "normal"
    return None


def _stable_id(source: str, text: str, idx: int) -> str:
    digest = hashlib.sha1(f"{source}|{idx}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"{source}:{digest}"


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".csv", ".tsv", ".txt", ".json", ".jsonl"}:
            yield p


def _read_text_file(path: Path) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def parse_fraud_call_text(text: str, source: str) -> list[dict[str, Any]]:
    """Parse 'label transcript...' lines (fraud/normal)."""
    rows: list[dict[str, Any]] = []
    for idx, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        # Common formats: "fraud <text>" / "normal <text>" or "label\ttext"
        m = re.match(r"^(fraud|normal|spam|ham)\s+(.+)$", line, flags=re.I)
        if not m:
            parts = re.split(r"[\t,]", line, maxsplit=1)
            if len(parts) != 2:
                continue
            label_raw, body = parts[0], parts[1]
        else:
            label_raw, body = m.group(1), m.group(2)
        label = _normalize_label(label_raw)
        body = body.strip().strip('"')
        if not label or not body:
            continue
        rows.append(
            {
                "id": _stable_id(source, body, idx),
                "text": body,
                "label": label,
                "source_dataset": source,
            }
        )
    return rows


def parse_sms_spam_collection(text: str, source: str) -> list[dict[str, Any]]:
    """Parse UCI SMSSpamCollection: 'label\\tmessage'."""
    rows: list[dict[str, Any]] = []
    for idx, line in enumerate(text.splitlines()):
        line = line.strip("\n")
        if not line:
            continue
        if "\t" in line:
            label_raw, body = line.split("\t", 1)
        else:
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            label_raw, body = parts
        label = _normalize_label(label_raw)
        body = body.strip()
        if not label or not body:
            continue
        rows.append(
            {
                "id": _stable_id(source, body, idx),
                "text": body,
                "label": label,
                "source_dataset": source,
            }
        )
    return rows


def parse_csv_generic(path: Path, source: str) -> list[dict[str, Any]]:
    """Best-effort CSV parser for spam/ham or fraud/normal tables."""
    content = _read_text_file(path)
    sample = content[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(content), dialect=dialect)
    if not reader.fieldnames:
        return []

    fields = [f.strip() for f in reader.fieldnames]
    lower = {f.lower(): f for f in fields}

    text_keys = [
        "msg",
        "message",
        "text",
        "sms",
        "content",
        "call transcript",
        "call_transcript",
        "transcript",
        "body",
    ]
    label_keys = ["label", "type of call", "type_of_call", "class", "category", "target", "y"]

    text_col = next((lower[k] for k in text_keys if k in lower), None)
    label_col = next((lower[k] for k in label_keys if k in lower), None)

    # Fallback: first two columns
    if text_col is None or label_col is None:
        if len(fields) >= 2:
            # Heuristic: shorter header name / known label values → label col
            label_col = label_col or fields[0]
            text_col = text_col or fields[1]
        else:
            return []

    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(reader):
        body = str(row.get(text_col, "") or "").strip()
        label = _normalize_label(str(row.get(label_col, "") or ""))
        if not body or not label:
            continue
        rows.append(
            {
                "id": _stable_id(source, body, idx),
                "text": body,
                "label": label,
                "source_dataset": source,
            }
        )
    return rows


def load_from_directory(path: Path, source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fp in _iter_files(path):
        name = fp.name.lower()
        if name.endswith(".csv") or name.endswith(".tsv"):
            rows.extend(parse_csv_generic(fp, source))
        elif "smsspamcollection" in name or name == "smsspamcollection":
            rows.extend(parse_sms_spam_collection(_read_text_file(fp), source))
        elif name.endswith(".txt"):
            text = _read_text_file(fp)
            # Prefer fraud/normal line format; else SMS spam format
            if re.search(r"^(fraud|normal)\b", text, flags=re.I | re.M):
                rows.extend(parse_fraud_call_text(text, source))
            elif re.search(r"^(spam|ham)\b", text, flags=re.I | re.M):
                rows.extend(parse_sms_spam_collection(text, source))
            else:
                rows.extend(parse_fraud_call_text(text, source))
    return rows


def fetch_fraud_call_india(use_kaggle: bool) -> list[dict[str, Any]]:
    source = "narayanyadav/fraud-call-india-dataset"
    dest = RAW_DIR / "fraud_call_india"
    dest.mkdir(parents=True, exist_ok=True)

    if use_kaggle:
        kpath = _download_kaggle_dataset(KAGGLE_DATASETS["fraud_call_india"], dest)
        if kpath:
            rows = load_from_directory(kpath, source)
            if rows:
                return rows
            # also scan dest
            rows = load_from_directory(dest, source)
            if rows:
                return rows

    print("  [fallback] downloading public fraud-call transcript corpus mirror…")
    data = _http_get(FRAUD_CALL_TXT)
    out = dest / "main_dataset_fcd.txt"
    out.write_bytes(data)
    return parse_fraud_call_text(data.decode("utf-8", errors="replace"), source)


def fetch_india_spam_sms(use_kaggle: bool) -> list[dict[str, Any]]:
    source = "junioralive/india-spam-sms-classification"
    dest = RAW_DIR / "india_spam_sms"
    dest.mkdir(parents=True, exist_ok=True)

    if use_kaggle:
        kpath = _download_kaggle_dataset(KAGGLE_DATASETS["india_spam_sms"], dest)
        if kpath:
            rows = load_from_directory(kpath, source)
            if rows:
                return rows
            rows = load_from_directory(dest, source)
            if rows:
                return rows

    print("  [fallback] downloading India SMS spam CSV (same dataset as Kaggle junioralive)…")
    data = _http_get(INDIA_SMS_CSV)
    out = dest / "spam_ham_india.csv"
    out.write_bytes(data)
    return parse_csv_generic(out, source)


def fetch_uci_sms_spam(use_kaggle: bool) -> list[dict[str, Any]]:
    source = "uciml/sms-spam-collection-dataset"
    dest = RAW_DIR / "uci_sms_spam"
    dest.mkdir(parents=True, exist_ok=True)

    if use_kaggle:
        kpath = _download_kaggle_dataset(KAGGLE_DATASETS["uci_sms_spam"], dest)
        if kpath:
            rows = load_from_directory(kpath, source)
            if rows:
                return rows
            rows = load_from_directory(dest, source)
            if rows:
                return rows

    print("  [fallback] downloading official UCI SMS Spam Collection zip…")
    blob = _http_get(UCI_SMS_ZIP)
    zip_path = dest / "sms+spam+collection.zip"
    zip_path.write_bytes(blob)
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(dest)
    # Find SMSSpamCollection file
    for fp in dest.rglob("*"):
        if fp.is_file() and fp.name.lower() in {"smsspamcollection", "smsspamcollection.txt"}:
            return parse_sms_spam_collection(_read_text_file(fp), source)
    # Some zips store without extension
    for fp in dest.rglob("*"):
        if fp.is_file() and "spam" in fp.name.lower() and fp.suffix == "":
            return parse_sms_spam_collection(_read_text_file(fp), source)
    return load_from_directory(dest, source)


def print_class_balance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    overall = Counter(r["label"] for r in rows)
    by_source: dict[str, Counter[str]] = {}
    for r in rows:
        by_source.setdefault(r["source_dataset"], Counter())[r["label"]] += 1

    total = sum(overall.values())
    majority = max(overall.values()) if overall else 0
    minority = min(overall.values()) if overall else 0
    ratio = (majority / minority) if minority else float("inf")
    imbalanced = ratio > IMBALANCE_RATIO_FLAG

    print("\n=== Class balance (label ∈ {fraud, normal}) ===")
    print(f"total_rows: {total}")
    for label, count in sorted(overall.items()):
        pct = 100.0 * count / total if total else 0.0
        print(f"  {label:8s}: {count:6d}  ({pct:5.1f}%)")
    print(f"majority/minority ratio: {ratio:.2f}  (flag if > {IMBALANCE_RATIO_FLAG})")
    if imbalanced:
        print(
            "⚠️  HEAVILY IMBALANCED — consider stratified sampling / class weights "
            "before training."
        )
    else:
        print("✓ Class balance within acceptable threshold for hackathon baselines.")

    print("\nPer source:")
    for source, counts in sorted(by_source.items()):
        parts = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"  {source}: {parts} (n={sum(counts.values())})")

    stats = {
        "total_rows": total,
        "overall": dict(overall),
        "majority_minority_ratio": None if ratio == float("inf") else round(ratio, 4),
        "imbalance_flag_threshold": IMBALANCE_RATIO_FLAG,
        "heavily_imbalanced": imbalanced,
        "by_source": {s: dict(c) for s, c in by_source.items()},
        "schema": ["id", "text", "label", "source_dataset"],
        "label_mapping": {
            "fraud": "fraud | scam | spam (normalized)",
            "normal": "normal | ham | legit (normalized)",
        },
        "disclaimer": (
            "Real multi-day digital-arrest video-call transcripts are not public. "
            "These real fraud-call/SMS corpora are proxies for scam language patterns, "
            "not verbatim digital-arrest evidence."
        ),
    }
    OUT_STATS.write_text(json.dumps(stats, indent=2))
    print(f"\nWrote stats -> {OUT_STATS}")
    return stats


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        key = hashlib.sha1(
            f"{r['source_dataset']}|{r['label']}|{r['text'].strip().lower()}".encode()
        ).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def main() -> int:
    print("HawkNet-Ai — scam transcript loader")
    print(
        "NOTE: digital-arrest live multi-day video-call transcripts are not public; "
        "using real fraud-call/SMS corpora as proxy.\n"
    )
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    use_kaggle = _ensure_kaggle_config()
    if use_kaggle:
        print("Kaggle credentials found — preferring Kaggle API downloads.")
    else:
        print(
            "No Kaggle credentials (~/.kaggle/kaggle.json or "
            "KAGGLE_USERNAME/KAGGLE_KEY). Using public mirrors of the same real datasets."
        )

    all_rows: list[dict[str, Any]] = []

    print("\n[1/3] Fraud Call Detection Dataset (India)")
    fraud_rows = fetch_fraud_call_india(use_kaggle)
    print(f"  loaded {len(fraud_rows)} rows")
    all_rows.extend(fraud_rows)

    print("\n[2/3] India Spam SMS Classification")
    india_sms = fetch_india_spam_sms(use_kaggle)
    print(f"  loaded {len(india_sms)} rows")
    all_rows.extend(india_sms)

    print("\n[3/3] UCI / Kaggle SMS Spam Collection")
    uci_rows = fetch_uci_sms_spam(use_kaggle)
    print(f"  loaded {len(uci_rows)} rows")
    all_rows.extend(uci_rows)

    all_rows = dedupe(all_rows)
    if not all_rows:
        print("ERROR: no rows loaded from any source.", file=sys.stderr)
        return 1

    with OUT_JSONL.open("w", encoding="utf-8") as fh:
        for row in all_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nWrote combined dataset -> {OUT_JSONL} ({len(all_rows)} rows)")

    print_class_balance(all_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

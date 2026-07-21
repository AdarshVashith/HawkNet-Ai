#!/usr/bin/env python3
"""Generate a synthetic transaction graph with one embedded mule-account ring.

Outputs (under data/fraud_graph/):
  accounts.csv, transactions.csv, device_links.csv, ground_truth.csv

ground_truth.csv is for evaluation only — do not feed into the detector.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RNG = random.Random(42)

N_ACCOUNTS = 50
N_TXNS = 200
N_DAYS = 30
RING_SIZE = 6
REPORTING_THRESHOLD = 50_000  # INR-like units; structuring stays just under
STRUCT_AMOUNT = 49_500

FIRST = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Anaya", "Aadhya", "Diya", "Myra", "Sara", "Ira",
    "Pari", "Anika", "Navya", "Kiara", "Rohan", "Kabir", "Yash", "Dev",
    "Neha", "Pooja", "Ritika", "Sneha", "Meera", "Kavya",
]
LAST = [
    "Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Khan", "Singh",
    "Gupta", "Mehta", "Joshi", "Das", "Chopra", "Malhotra", "Bose", "Rao",
]


def utc_start() -> datetime:
    return datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def gen_accounts() -> list[dict]:
    accounts = []
    for i in range(1, N_ACCOUNTS + 1):
        acc_id = f"ACC{i:03d}"
        name = f"{RNG.choice(FIRST)} {RNG.choice(LAST)}"
        phone = f"+9198{RNG.randint(10000000, 99999999)}"
        device = f"DEV{RNG.randint(1000, 9999)}"
        accounts.append(
            {
                "account_id": acc_id,
                "holder_name": name,
                "phone": phone,
                "primary_device_id": device,
                "account_type": RNG.choice(["savings", "current", "wallet"]),
                "opened_at": iso(utc_start() - timedelta(days=RNG.randint(60, 900))),
                "city": RNG.choice(["Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Pune", "Kolkata"]),
            }
        )
    return accounts


def embed_mule_ring(accounts: list[dict]) -> tuple[list[str], list[dict], list[dict]]:
    """Return ring account ids, mutated accounts, and device_links rows."""
    ring_ids = [f"ACC{i:03d}" for i in range(1, RING_SIZE + 1)]
    # Shared phones/devices across 3+ 'unrelated' accounts
    shared_phone_a = "+919811112222"
    shared_phone_b = "+919833334444"
    shared_device_a = "DEV-MULE-01"
    shared_device_b = "DEV-MULE-02"

    by_id = {a["account_id"]: a for a in accounts}
    # Accounts 1,2,3 share phone A + device A; 4,5,6 share phone B + device B;
    # also cross-link device A onto account 4 to densify shared-device graph.
    for aid in ring_ids[:3]:
        by_id[aid]["phone"] = shared_phone_a
        by_id[aid]["primary_device_id"] = shared_device_a
        by_id[aid]["holder_name"] = by_id[aid]["holder_name"]  # keep distinct names
    for aid in ring_ids[3:]:
        by_id[aid]["phone"] = shared_phone_b
        by_id[aid]["primary_device_id"] = shared_device_b
    by_id["ACC004"]["primary_device_id"] = shared_device_a  # cross-share

    device_links = []
    # Explicit multi-device links for ring (simulates login fingerprints)
    for aid in ring_ids[:4]:
        device_links.append(
            {
                "account_id": aid,
                "device_id": shared_device_a,
                "phone": shared_phone_a if aid in ring_ids[:3] else by_id[aid]["phone"],
                "first_seen": iso(utc_start() + timedelta(days=1)),
                "last_seen": iso(utc_start() + timedelta(days=N_DAYS - 1)),
                "link_type": "login_fingerprint",
            }
        )
    for aid in ring_ids[2:]:
        device_links.append(
            {
                "account_id": aid,
                "device_id": shared_device_b,
                "phone": shared_phone_b if aid in ring_ids[3:] else by_id[aid]["phone"],
                "first_seen": iso(utc_start() + timedelta(days=2)),
                "last_seen": iso(utc_start() + timedelta(days=N_DAYS - 2)),
                "link_type": "login_fingerprint",
            }
        )

    # Normal accounts: one device link matching primary
    for a in accounts:
        if a["account_id"] in ring_ids:
            continue
        device_links.append(
            {
                "account_id": a["account_id"],
                "device_id": a["primary_device_id"],
                "phone": a["phone"],
                "first_seen": a["opened_at"],
                "last_seen": iso(utc_start() + timedelta(days=N_DAYS)),
                "link_type": "primary",
            }
        )

    return ring_ids, accounts, device_links


def gen_normal_transactions(accounts: list[dict], ring_ids: set[str], n: int) -> list[dict]:
    txns = []
    non_ring = [a["account_id"] for a in accounts if a["account_id"] not in ring_ids]
    merchants = [f"MERCH{i:02d}" for i in range(1, 16)]
    start = utc_start()
    for i in range(n):
        src = RNG.choice(non_ring)
        if RNG.random() < 0.55:
            dst = RNG.choice([x for x in non_ring if x != src])
            ttype = "p2p"
        else:
            dst = RNG.choice(merchants)
            ttype = "merchant"
        ts = start + timedelta(
            days=RNG.randint(0, N_DAYS - 1),
            hours=RNG.randint(0, 23),
            minutes=RNG.randint(0, 59),
        )
        amount = round(RNG.uniform(200, 25_000), 2)
        txns.append(
            {
                "txn_id": f"TXN{i+1:04d}",
                "src_account": src,
                "dst_account": dst,
                "amount": amount,
                "currency": "INR",
                "txn_type": ttype,
                "timestamp": iso(ts),
                "channel": RNG.choice(["upi", "imps", "neft", "card"]),
            }
        )
    return txns


def gen_mule_transactions(ring_ids: list[str], start_idx: int) -> list[dict]:
    """Rapid pass-through + structuring just under reporting threshold."""
    txns = []
    start = utc_start() + timedelta(days=5, hours=10)
    idx = start_idx
    # Entry funds into first mule from external-looking non-ring sources
    feeders = [f"ACC{i:03d}" for i in range(RING_SIZE + 1, RING_SIZE + 8)]
    t = start
    for day in range(6):
        # Structure entries just under threshold into ACC001 / ACC002
        for feeder, mule in zip(feeders, ring_ids[:3] * 3):
            amount = STRUCT_AMOUNT - RNG.randint(0, 400)
            txns.append(
                {
                    "txn_id": f"TXN{idx:04d}",
                    "src_account": feeder,
                    "dst_account": mule,
                    "amount": float(amount),
                    "currency": "INR",
                    "txn_type": "p2p",
                    "timestamp": iso(t),
                    "channel": "imps",
                }
            )
            idx += 1
            # Rapid pass-through within hours along the ring
            t_pass = t + timedelta(hours=RNG.randint(1, 4), minutes=RNG.randint(5, 50))
            next_mule = ring_ids[(ring_ids.index(mule) + 1) % len(ring_ids)]
            txns.append(
                {
                    "txn_id": f"TXN{idx:04d}",
                    "src_account": mule,
                    "dst_account": next_mule,
                    "amount": float(amount - RNG.randint(50, 300)),
                    "currency": "INR",
                    "txn_type": "p2p",
                    "timestamp": iso(t_pass),
                    "channel": "upi",
                }
            )
            idx += 1
            t = t_pass + timedelta(hours=RNG.randint(1, 3))
        t = start + timedelta(days=day + 1, hours=9)
    return txns


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main() -> int:
    accounts = gen_accounts()
    ring_ids, accounts, device_links = embed_mule_ring(accounts)
    ring_set = set(ring_ids)

    normal_n = N_TXNS - 60
    normal = gen_normal_transactions(accounts, ring_set, max(normal_n, 100))
    mule = gen_mule_transactions(ring_ids, start_idx=len(normal) + 1)
    txns = normal + mule
    # Trim / pad to ~200
    if len(txns) > N_TXNS:
        # keep all mule txns, trim normal
        mule_ids = {t["txn_id"] for t in mule}
        normal_kept = [t for t in txns if t["txn_id"] not in mule_ids][: N_TXNS - len(mule)]
        txns = normal_kept + mule
    # renumber txn ids
    for i, t in enumerate(txns, start=1):
        t["txn_id"] = f"TXN{i:04d}"

    ground_truth = []
    for a in accounts:
        ground_truth.append(
            {
                "account_id": a["account_id"],
                "is_mule_ring": int(a["account_id"] in ring_set),
                "ring_id": "RING-MULE-01" if a["account_id"] in ring_set else "",
                "role": (
                    "entry" if a["account_id"] in ring_ids[:2]
                    else "pass_through" if a["account_id"] in ring_set
                    else "benign"
                ),
            }
        )

    write_csv(
        ROOT / "accounts.csv",
        accounts,
        ["account_id", "holder_name", "phone", "primary_device_id", "account_type", "opened_at", "city"],
    )
    write_csv(
        ROOT / "transactions.csv",
        txns,
        ["txn_id", "src_account", "dst_account", "amount", "currency", "txn_type", "timestamp", "channel"],
    )
    write_csv(
        ROOT / "device_links.csv",
        device_links,
        ["account_id", "device_id", "phone", "first_seen", "last_seen", "link_type"],
    )
    write_csv(
        ROOT / "ground_truth.csv",
        ground_truth,
        ["account_id", "is_mule_ring", "ring_id", "role"],
    )

    print(f"accounts={len(accounts)} transactions={len(txns)} device_links={len(device_links)}")
    print(f"mule_ring={ring_ids}")
    print(f"Wrote CSVs under {ROOT}")
    print("NOTE: ground_truth.csv is evaluation-only — do not feed into the model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

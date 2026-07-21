"""NetworkX fraud-graph construction, community detection, and suspicion scoring.

Builds a heterogeneous graph of accounts / phones / devices with edges from
transactions and shared-attribute links. Communities are detected via Louvain
(if python-louvain is installed) or NetworkX greedy_modularity_communities.

Suspicion score per account-community uses:
  - pass-through velocity (funds in then out within hours)
  - structuring pattern (amounts just under a reporting threshold)
  - shared-device / shared-phone density

Evaluation against data/fraud_graph/ground_truth.csv is available via
``evaluate_against_ground_truth`` (GT is never used for scoring).
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx

MODEL_VERSION = "fraud-graph-nx-0.1.0"
REPORTING_THRESHOLD = 50_000.0
STRUCT_BAND = (45_000.0, 49_999.0)
PASS_THROUGH_HOURS = 6.0

def _find_data_dir() -> Path:
    """Locate data/fraud_graph by walking up from this file."""
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        candidate = parent / "data" / "fraud_graph"
        if (candidate / "accounts.csv").is_file() or candidate.is_dir():
            # Prefer a dir that already has CSVs; otherwise first fraud_graph dir
            if (candidate / "accounts.csv").is_file():
                return candidate
    # Fallback: repo layout .../backend/app/models/fraud_graph -> parents[3]
    return Path(__file__).resolve().parents[3] / "data" / "fraud_graph"


DEFAULT_DATA = _find_data_dir()


def _parse_ts(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@dataclass
class ClusterResult:
    cluster_id: str
    rank: int
    suspicion_score: float
    member_accounts: list[str]
    member_phones: list[str] = field(default_factory=list)
    member_devices: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    signals: dict[str, float] = field(default_factory=dict)
    size: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "rank": self.rank,
            "suspicion_score": round(self.suspicion_score, 4),
            "member_accounts": self.member_accounts,
            "member_phones": self.member_phones,
            "member_devices": self.member_devices,
            "evidence": self.evidence,
            "signals": {k: round(v, 4) for k, v in self.signals.items()},
            "size": self.size or len(self.member_accounts),
        }


class FraudGraphIntelligence:
    """Build graph, detect communities, rank by mule-ring suspicion."""

    version = MODEL_VERSION

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA
        self.graph: nx.Graph | None = None
        self.accounts: list[dict[str, str]] = []
        self.transactions: list[dict[str, str]] = []
        self.device_links: list[dict[str, str]] = []
        self._clusters: list[ClusterResult] = []
        self._by_id: dict[str, ClusterResult] = {}

    def load(self) -> None:
        self.accounts = _load_csv(self.data_dir / "accounts.csv")
        self.transactions = _load_csv(self.data_dir / "transactions.csv")
        self.device_links = _load_csv(self.data_dir / "device_links.csv")

    def build_graph(self) -> nx.Graph:
        if not self.accounts:
            self.load()
        G = nx.Graph()

        for a in self.accounts:
            aid = a["account_id"]
            G.add_node(aid, ntype="account", **a)
            phone = a.get("phone") or ""
            device = a.get("primary_device_id") or ""
            if phone:
                pid = f"phone:{phone}"
                G.add_node(pid, ntype="phone", phone=phone)
                G.add_edge(aid, pid, etype="has_phone", weight=1.5, amount=0.0, count=1)
            if device:
                did = f"device:{device}"
                G.add_node(did, ntype="device", device_id=device)
                G.add_edge(aid, did, etype="has_device", weight=1.5, amount=0.0, count=1)

        for link in self.device_links:
            aid = link["account_id"]
            if aid not in G:
                G.add_node(aid, ntype="account", account_id=aid)
            did = f"device:{link['device_id']}"
            G.add_node(did, ntype="device", device_id=link["device_id"])
            if G.has_edge(aid, did):
                G[aid][did]["weight"] += 1.0
                G[aid][did]["count"] += 1
            else:
                G.add_edge(aid, did, etype="device_link", weight=2.0, amount=0.0, count=1)
            phone = link.get("phone") or ""
            if phone:
                pid = f"phone:{phone}"
                G.add_node(pid, ntype="phone", phone=phone)
                if G.has_edge(aid, pid):
                    G[aid][pid]["weight"] += 0.5
                    G[aid][pid]["count"] += 1
                else:
                    G.add_edge(aid, pid, etype="link_phone", weight=1.2, amount=0.0, count=1)

        # Transaction edges between accounts (aggregate frequency/amount/recency)
        now = max((_parse_ts(t["timestamp"]) for t in self.transactions), default=datetime.now(timezone.utc))
        agg: dict[tuple[str, str], dict[str, float]] = defaultdict(
            lambda: {"amount": 0.0, "count": 0.0, "recency": 0.0}
        )
        for t in self.transactions:
            src, dst = t["src_account"], t["dst_account"]
            if not src.startswith("ACC") or not dst.startswith("ACC"):
                # still include merchant sinks as nodes lightly
                if not dst.startswith("ACC"):
                    G.add_node(dst, ntype="merchant")
            key = tuple(sorted((src, dst)))
            amount = float(t["amount"])
            ts = _parse_ts(t["timestamp"])
            age_days = max((now - ts).total_seconds() / 86400.0, 0.0)
            recency = math.exp(-age_days / 14.0)
            agg[key]["amount"] += amount
            agg[key]["count"] += 1
            agg[key]["recency"] = max(agg[key]["recency"], recency)

        for (a, b), stats in agg.items():
            if a not in G:
                G.add_node(a, ntype="account" if a.startswith("ACC") else "other")
            if b not in G:
                G.add_node(b, ntype="account" if b.startswith("ACC") else "other")
            # weight: log amount * frequency * recency
            w = math.log1p(stats["amount"]) * (1.0 + 0.3 * stats["count"]) * (0.5 + 0.5 * stats["recency"])
            if G.has_edge(a, b):
                G[a][b]["weight"] += w
                G[a][b]["amount"] += stats["amount"]
                G[a][b]["count"] += stats["count"]
            else:
                G.add_edge(
                    a,
                    b,
                    etype="transaction",
                    weight=float(w),
                    amount=float(stats["amount"]),
                    count=int(stats["count"]),
                )

        self.graph = G
        return G

    def _detect_communities(self, G: nx.Graph) -> list[set[str]]:
        # Prefer Louvain
        try:
            import community as community_louvain  # python-louvain

            partition = community_louvain.best_partition(G, weight="weight", random_state=42)
            groups: dict[int, set[str]] = defaultdict(set)
            for node, cid in partition.items():
                groups[cid].add(node)
            return list(groups.values())
        except Exception:
            pass
        try:
            from networkx.algorithms.community import greedy_modularity_communities

            comms = greedy_modularity_communities(G, weight="weight")
            return [set(c) for c in comms]
        except Exception:
            # Fallback: connected components
            return [set(c) for c in nx.connected_components(G)]

    def _pass_through_velocity(self, accounts: set[str]) -> tuple[float, int]:
        """Score rapid in-then-out patterns within PASS_THROUGH_HOURS."""
        by_acc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for t in self.transactions:
            if t["src_account"] in accounts or t["dst_account"] in accounts:
                by_acc[t["dst_account"] if t["dst_account"] in accounts else ""].append(t)
                by_acc[t["src_account"] if t["src_account"] in accounts else ""].append(t)

        # Build per-account in/out lists
        ins: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        outs: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        for t in self.transactions:
            ts = _parse_ts(t["timestamp"])
            amt = float(t["amount"])
            if t["dst_account"] in accounts and t["dst_account"].startswith("ACC"):
                ins[t["dst_account"]].append((ts, amt))
            if t["src_account"] in accounts and t["src_account"].startswith("ACC"):
                outs[t["src_account"]].append((ts, amt))

        hits = 0
        checked = 0
        for acc in accounts:
            if not acc.startswith("ACC"):
                continue
            for tin, ain in ins.get(acc, []):
                for tout, aout in outs.get(acc, []):
                    if tout <= tin:
                        continue
                    hours = (tout - tin).total_seconds() / 3600.0
                    if hours <= PASS_THROUGH_HOURS and aout >= 0.7 * ain:
                        hits += 1
                    checked += 1
        if hits == 0:
            return 0.0, 0
        score = min(1.0, hits / max(len([a for a in accounts if a.startswith("ACC")]), 1) * 0.5 + min(hits, 10) / 10.0)
        return float(score), hits

    def _structuring_score(self, accounts: set[str]) -> tuple[float, int]:
        lo, hi = STRUCT_BAND
        count = 0
        for t in self.transactions:
            if t["src_account"] not in accounts and t["dst_account"] not in accounts:
                continue
            if not (t["src_account"].startswith("ACC") or t["dst_account"].startswith("ACC")):
                continue
            amt = float(t["amount"])
            if lo <= amt <= hi:
                count += 1
        score = min(1.0, count / 8.0)
        return float(score), count

    def _shared_device_density(self, nodes: set[str]) -> tuple[float, int, int]:
        accounts = {n for n in nodes if n.startswith("ACC")}
        devices = {n for n in nodes if n.startswith("device:")}
        phones = {n for n in nodes if n.startswith("phone:")}
        # density: shared devices connecting multiple accounts
        multi_device = 0
        for d in devices:
            nbrs = [n for n in self.graph.neighbors(d) if n in accounts] if self.graph else []
            if len(nbrs) >= 3:
                multi_device += 1
        multi_phone = 0
        for p in phones:
            nbrs = [n for n in self.graph.neighbors(p) if n in accounts] if self.graph else []
            if len(nbrs) >= 3:
                multi_phone += 1
        score = min(1.0, 0.55 * multi_device + 0.45 * multi_phone)
        if len(accounts) >= 3 and (multi_device or multi_phone):
            score = max(score, 0.5)
        return float(min(score, 1.0)), multi_device, multi_phone

    def _merge_related_communities(self, communities: list[set[str]]) -> list[set[str]]:
        """Merge communities that share multi-account devices/phones or mule-like links.

        Louvain sometimes splits one mule ring across 2 communities (e.g. shared
        phone-A clique vs phone-B clique). For intelligence packaging we recombine
        communities that share a device/phone used by 3+ accounts, or that exchange
        rapid structured transfers with each other.
        """
        if self.graph is None or len(communities) <= 1:
            return communities

        G = self.graph
        # Map account -> community index
        acc_to_comm: dict[str, int] = {}
        for i, nodes in enumerate(communities):
            for n in nodes:
                if n.startswith("ACC"):
                    acc_to_comm[n] = i

        parent = list(range(len(communities)))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        # 1) Merge communities sharing a device/phone linked to 3+ accounts
        for node, data in G.nodes(data=True):
            if data.get("ntype") not in {"device", "phone"}:
                continue
            acc_nbrs = [n for n in G.neighbors(node) if n.startswith("ACC")]
            if len(acc_nbrs) < 3:
                continue
            comms = {acc_to_comm[a] for a in acc_nbrs if a in acc_to_comm}
            comms = list(comms)
            for i in range(1, len(comms)):
                union(comms[0], comms[i])

        # 2) Also merge communities that exchange structured ring traffic
        # between accounts that already sit on multi-share devices (core ring only).
        multi_share_accounts: set[str] = set()
        for node, data in G.nodes(data=True):
            if data.get("ntype") not in {"device", "phone"}:
                continue
            acc_nbrs = [n for n in G.neighbors(node) if n.startswith("ACC")]
            if len(acc_nbrs) >= 3:
                multi_share_accounts.update(acc_nbrs)

        structured_links: dict[tuple[int, int], int] = {}
        lo, hi = STRUCT_BAND
        for t in self.transactions:
            src, dst = t["src_account"], t["dst_account"]
            if src not in multi_share_accounts or dst not in multi_share_accounts:
                continue
            if src not in acc_to_comm or dst not in acc_to_comm:
                continue
            c1, c2 = acc_to_comm[src], acc_to_comm[dst]
            if c1 == c2:
                continue
            amt = float(t["amount"])
            if lo <= amt <= hi:
                key = tuple(sorted((c1, c2)))
                structured_links[key] = structured_links.get(key, 0) + 1
        for (c1, c2), cnt in structured_links.items():
            if cnt >= 2:
                union(c1, c2)

        merged: dict[int, set[str]] = {}
        for i, nodes in enumerate(communities):
            root = find(i)
            merged.setdefault(root, set()).update(nodes)
        return list(merged.values())

    def score_communities(self) -> list[ClusterResult]:
        if self.graph is None:
            self.build_graph()
        assert self.graph is not None
        G = self.graph
        communities = self._merge_related_communities(self._detect_communities(G))

        results: list[ClusterResult] = []
        for i, nodes in enumerate(communities):
            accounts = sorted(n for n in nodes if n.startswith("ACC"))
            if len(accounts) < 2:
                continue
            phones = sorted(n.split("phone:", 1)[1] for n in nodes if n.startswith("phone:"))
            devices = sorted(n.split("device:", 1)[1] for n in nodes if n.startswith("device:"))

            pt_score, pt_hits = self._pass_through_velocity(set(accounts))
            st_score, st_count = self._structuring_score(set(accounts))
            sd_score, multi_dev, multi_phone = self._shared_device_density(nodes)

            suspicion = 0.4 * pt_score + 0.35 * st_score + 0.25 * sd_score
            # slight boost for larger tightly-linked mule-sized rings
            if 4 <= len(accounts) <= 10:
                suspicion = min(1.0, suspicion + 0.05)

            evidence = []
            if pt_hits:
                evidence.append(
                    f"Pass-through velocity: {pt_hits} in→out pairs within {PASS_THROUGH_HOURS:.0f}h"
                )
            if st_count:
                evidence.append(
                    f"Structuring: {st_count} transfers in band "
                    f"{STRUCT_BAND[0]:.0f}-{STRUCT_BAND[1]:.0f} (threshold {REPORTING_THRESHOLD:.0f})"
                )
            if multi_dev:
                evidence.append(f"Shared-device density: {multi_dev} device(s) linked to 3+ accounts")
            if multi_phone:
                evidence.append(f"Shared-phone density: {multi_phone} phone(s) linked to 3+ accounts")
            if not evidence:
                evidence.append("No strong mule-ring signals; low baseline community score")

            results.append(
                ClusterResult(
                    cluster_id=f"cluster-{i+1:02d}",
                    rank=0,
                    suspicion_score=float(suspicion),
                    member_accounts=accounts,
                    member_phones=phones,
                    member_devices=devices,
                    evidence=evidence,
                    signals={
                        "pass_through_velocity": pt_score,
                        "structuring": st_score,
                        "shared_device_density": sd_score,
                    },
                    size=len(accounts),
                )
            )

        results.sort(key=lambda c: c.suspicion_score, reverse=True)
        for rank, c in enumerate(results, start=1):
            c.rank = rank
            c.cluster_id = f"cluster-{rank:02d}"

        self._clusters = results
        self._by_id = {c.cluster_id: c for c in results}
        return results

    def get_clusters(self) -> list[dict[str, Any]]:
        if not self._clusters:
            self.score_communities()
        return [c.as_dict() for c in self._clusters]

    def get_cluster(self, cluster_id: str) -> ClusterResult | None:
        if not self._clusters:
            self.score_communities()
        return self._by_id.get(cluster_id)

    def evaluate_against_ground_truth(self) -> dict[str, Any]:
        """Compare top clusters to ground_truth.csv (evaluation only)."""
        gt_path = self.data_dir / "ground_truth.csv"
        if not gt_path.is_file():
            return {"error": "ground_truth.csv not found"}
        gt_rows = _load_csv(gt_path)
        mule = {r["account_id"] for r in gt_rows if r.get("is_mule_ring") in {"1", "true", "True"}}
        if not self._clusters:
            self.score_communities()
        best_rank = None
        best_recall = 0.0
        best_id = None
        for c in self._clusters:
            hit = set(c.member_accounts) & mule
            recall = len(hit) / max(len(mule), 1)
            prec = len(hit) / max(len(c.member_accounts), 1)
            if recall > best_recall or (
                recall == best_recall and best_rank is not None and c.rank < best_rank
            ):
                best_recall = recall
                best_rank = c.rank
                best_id = c.cluster_id
                best_prec = prec
                best_hit = sorted(hit)
        surfaced = best_recall >= 0.5  # majority of ring members in one cluster
        # Also report coverage if top-2 clusters are read together (pre-merge baseline)
        top2_accounts: set[str] = set()
        for c in self._clusters[:2]:
            top2_accounts.update(c.member_accounts)
        top2_hit = sorted(top2_accounts & mule)
        top2_recall = len(top2_hit) / max(len(mule), 1)

        return {
            "mule_accounts": sorted(mule),
            "surfaced": surfaced,
            "best_cluster_id": best_id,
            "best_rank": best_rank,
            "best_recall": round(best_recall, 4),
            "best_precision": round(best_prec, 4) if best_id else None,
            "best_hit_accounts": best_hit if best_id else [],
            "top2_combined_recall": round(top2_recall, 4),
            "top2_combined_hit_accounts": top2_hit,
            "note": "ground_truth used only for evaluation — not for scoring",
        }


# Module-level singleton for API reuse
_intel: FraudGraphIntelligence | None = None


def get_intelligence(data_dir: Path | None = None, refresh: bool = False) -> FraudGraphIntelligence:
    global _intel
    if _intel is None or refresh:
        _intel = FraudGraphIntelligence(data_dir=data_dir)
        _intel.build_graph()
        _intel.score_communities()
    return _intel

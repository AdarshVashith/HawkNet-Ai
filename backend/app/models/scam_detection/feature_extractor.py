"""Feature extraction for scam / fraud call and SMS transcripts.

Extracts interpretable signals commonly seen in Indian digital-arrest and
authority-impersonation scams, plus general urgency / payment pressure cues.

NOTE: Training data is real public fraud-call + SMS corpora (see
``data/scam_transcripts/``). Live multi-day digital-arrest video-call
transcripts are not public; these features are designed to capture the
*language patterns* of those scams as a proxy, not claim verbatim case data.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


# Authority / agency impersonation (India-focused + common bank/telecom lures)
IMPERSONATION_KEYWORDS: tuple[str, ...] = (
    "cbi",
    "central bureau of investigation",
    "enforcement directorate",
    " ed ",
    "customs",
    "cyber crime",
    "cybercrime",
    "police",
    "rbi",
    "reserve bank",
    "income tax",
    "it department",
    "narcotics",
    "ncb",
    "digital arrest",
    "digitalarrest",
    "aadhaar linked to crime",
    "aadhar linked to crime",
    "aadhaar linked",
    "aadhar linked",
    "court warrant",
    "arrest warrant",
    "bank manager",
    "customer care",
    "kyc department",
    "from the court",
    "government of india",
    "ministry of",
)

URGENCY_PATTERNS: tuple[str, ...] = (
    r"\burgent\b",
    r"\bimmediately\b",
    r"\bwithin\s+\d+\s*(hour|hr|min|minute|day)s?\b",
    r"\blast\s+chance\b",
    r"\bact\s+now\b",
    r"\bright\s+now\b",
    r"\bexpire[sd]?\b",
    r"\bsuspend(ed|ing)?\b",
    r"\bblock(ed|ing)?\b",
    r"\bfinal\s+warning\b",
    r"\bdo\s+not\s+ignore\b",
    r"\bimmediate\s+action\b",
    r"\bbefore\s+it\s+is\s+too\s+late\b",
    r"\bwithin\s+24\s*hours?\b",
    r"\baccount\s+will\s+be\s+closed\b",
    # Prize / lottery / win — very common in Indian SMS scams
    r"\bwin\b.*\b(prize|money|cash|rupee|lakh|crore|reward)\b",
    r"\bwon\b.*\b(prize|lucky|draw|lottery|crore|lakh)\b",
    r"\bcongratulations?\b",
    r"\bcongrats?\b",
    r"\blottery\b",
    r"\bprize\b.*\bwon\b",
    r"\bselected\b.*\b(winner|lucky|draw)\b",
    r"\bclaim\s+(your|the)?\s*(prize|reward|money|cash)\b",
    r"\bfree\s*(gift|iphone|ipad|laptop|car|bike)\b",
    r"\bwithin\s+minutes?\b",
    r"\binstantly?\b.*\b(money|cash|transfer|credit)\b",
    r"\bget\s+rs\.?\s*\d+",
    r"\bwin\s+rs\.?\s*\d+",
)

ISOLATION_PATTERNS: tuple[str, ...] = (
    r"\bdon'?t\s+(tell|inform|share|call)\b",
    r"\bdo\s+not\s+(tell|inform|share|disconnect|hang\s*up)\b",
    r"\bkeep\s+this\s+confidential\b",
    r"\bstay\s+on\s+(the\s+)?(line|call)\b",
    r"\bdo\s+not\s+disconnect\b",
    r"\bdon'?t\s+disconnect\b",
    r"\bdon'?t\s+hang\s*up\b",
    r"\bdo\s+not\s+hang\s*up\b",
    r"\btalk\s+to\s+no\s+one\b",
    r"\bdo\s+not\s+speak\s+to\s+anyone\b",
    r"\bsecret\b",
    r"\balone\b.*\b(room|house)\b",
    r"\bkeep\s+your\s+phone\s+with\s+you\b",
)

# Additional high-signal scam keywords (standalone pattern matches add to score)
SCAM_KEYWORD_PATTERNS: tuple[str, ...] = (
    r"\bclick\s+(this|the|here|link|below)\b",
    r"\btap\s+(here|this|link|below)\b",
    r"\bbit\.ly\b",
    r"\btinyurl\b",
    r"\bgoo\.gl\b",
    r"\bt\.co\b",
    r"\bshort\s*url\b",
    r"\bhttp[:/]{2,3}\d",          # malformed URLs like http//3001
    r"\bhttp[:/]{2,3}[a-z0-9-]+\.\b",  # any link
    r"\bverify\s+(your|account|kyc|bank|card|number)\b",
    r"\bunlock\s+(your|the)?\s*(account|card|limit)\b",
    r"\bupdate\s+(your)?\s*(kyc|aadhar|pan|details?|information)\b",
    r"\bfrozen?\b.*\baccount\b",
    r"\baccount\s+(frozen?|suspended?|blocked?|closed?)\b",
    r"\b\d{5,}\s*(rupees?|rs\.?|lakh|crore)\b",  # large monetary amounts
    r"\bsend\s+(money|cash|funds)\b",
    r"\btransfer\s+(money|funds|cash|rupees?)\b",
    r"\bdownload\s+(this|the)?\s*(app|apk|link)\b",
    r"\binstall\s+(this|the)?\s*(app|software)\b",
    r"\bforward\s+this\b",
    r"\bshare\s+your\s+(otp|pin|password|cvv)\b",
)

VIDEO_HOLD_PATTERNS: tuple[str, ...] = (
    r"\bvideo\s*(call|conference|meeting|link)?\b",
    r"\bzoom\b",
    r"\bgoogle\s+meet\b",
    r"\bms\s+teams\b",
    r"\bkeep\s+(the\s+)?camera\s+on\b",
    r"\bturn\s+on\s+(your\s+)?camera\b",
    r"\bstay\s+on\s+video\b",
    r"\bdo\s+not\s+leave\s+the\s+(call|meeting)\b",
    r"\bvirtual\s+court\b",
    r"\bonline\s+hearing\b",
)

PAYMENT_OTP_PATTERNS: tuple[str, ...] = (
    r"\botp\b",
    r"\bone[\s-]?time\s+password\b",
    r"\bpin\b",
    r"\bcvv\b",
    r"\bupi\b",
    r"\bgpay\b",
    r"\bphonepe\b",
    r"\bpaytm\b",
    r"\bbank\s+account\b",
    r"\baccount\s+number\b",
    r"\bifsc\b",
    r"\bwire\s+transfer\b",
    r"\bgift\s+card\b",
    r"\bcrypto\b",
    r"\bwallet\b",
    r"\bpay\s+(now|immediately|fine|penalty|fee)\b",
    r"\btransfer\s+(money|funds|amount)\b",
    r"\bdebit\s+card\b",
    r"\bcredit\s+card\b",
    r"\bnet\s*banking\b",
    r"\bkyc\b",
    r"\baadhaar\b",
    r"\baadhar\b",
    r"\bpan\s+card\b",
)


@dataclass
class TranscriptFeatures:
    """Structured features extracted from a single transcript / message."""

    impersonation_keyword_count: int
    impersonation_density: float
    impersonation_hits: list[str]
    urgency_score: float
    isolation_score: float
    request_for_video_hold: bool
    payment_otp_request: bool
    token_count: int
    char_count: int
    url_count: int

    def as_numeric_dict(self) -> dict[str, float]:
        """Flat numeric features for sklearn (no free-text lists)."""
        return {
            "impersonation_keyword_count": float(self.impersonation_keyword_count),
            "impersonation_density": float(self.impersonation_density),
            "urgency_score": float(self.urgency_score),
            "isolation_score": float(self.isolation_score),
            "request_for_video_hold": 1.0 if self.request_for_video_hold else 0.0,
            "payment_otp_request": 1.0 if self.payment_otp_request else 0.0,
            "token_count": float(self.token_count),
            "char_count": float(self.char_count),
            "url_count": float(self.url_count),
        }

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


FEATURE_NAMES: list[str] = list(
    TranscriptFeatures(
        impersonation_keyword_count=0,
        impersonation_density=0.0,
        impersonation_hits=[],
        urgency_score=0.0,
        isolation_score=0.0,
        request_for_video_hold=False,
        payment_otp_request=False,
        token_count=0,
        char_count=0,
        url_count=0,
    ).as_numeric_dict().keys()
)


def _normalize(text: str) -> str:
    # Pad so boundary-sensitive keywords like " ed " still match mid-string.
    return f" {text.lower()} "


def _pattern_hit_rate(text: str, patterns: tuple[str, ...]) -> tuple[float, int]:
    hits = 0
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits += 1
    score = hits / max(len(patterns), 1)
    return score, hits


def extract_features(text: str) -> TranscriptFeatures:
    """Extract scam-oriented features from a transcript or SMS body."""
    raw = text or ""
    norm = _normalize(raw)
    tokens = re.findall(r"[a-z0-9']+", norm)
    token_count = max(len(tokens), 1)

    hits: list[str] = []
    for kw in IMPERSONATION_KEYWORDS:
        if kw in norm:
            hits.append(kw.strip())
    # de-dupe while preserving order
    seen: set[str] = set()
    impersonation_hits = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            impersonation_hits.append(h)

    impersonation_count = len(impersonation_hits)
    impersonation_density = impersonation_count / token_count

    urgency_score, _ = _pattern_hit_rate(norm, URGENCY_PATTERNS)
    isolation_score, _ = _pattern_hit_rate(norm, ISOLATION_PATTERNS)

    # Boost urgency_score with scam keyword hits (each match adds 0.15, capped at 1.0)
    scam_kw_hits, scam_kw_count = _pattern_hit_rate(norm, SCAM_KEYWORD_PATTERNS)
    urgency_score = min(1.0, urgency_score + scam_kw_hits * 0.6)

    video_hold = any(re.search(p, norm, flags=re.I) for p in VIDEO_HOLD_PATTERNS)
    payment_otp = any(re.search(p, norm, flags=re.I) for p in PAYMENT_OTP_PATTERNS)
    # Broader URL detection: catches https://, http://, http//, www., bit.ly, etc.
    url_count = len(re.findall(r"https?:[/\\]+|http[/\\]{2,}|www\.|bit\.ly|tinyurl|goo\.gl", norm, flags=re.I))

    return TranscriptFeatures(
        impersonation_keyword_count=impersonation_count,
        impersonation_density=round(impersonation_density, 6),
        impersonation_hits=impersonation_hits,
        urgency_score=round(urgency_score, 4),
        isolation_score=round(isolation_score, 4),
        request_for_video_hold=video_hold,
        payment_otp_request=payment_otp,
        token_count=len(tokens),
        char_count=len(raw),
        url_count=url_count,
    )


def extract_numeric_features(text: str) -> dict[str, float]:
    return extract_features(text).as_numeric_dict()


def features_matrix(texts: list[str]) -> list[list[float]]:
    """Return rows ordered by FEATURE_NAMES for stacking with TF-IDF."""
    rows: list[list[float]] = []
    for text in texts:
        feats = extract_numeric_features(text)
        rows.append([feats[name] for name in FEATURE_NAMES])
    return rows

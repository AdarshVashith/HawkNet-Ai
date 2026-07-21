"""
Grounding safety check for AI-generated FIR narratives.

Extracts dates, rupee amounts, and proper nouns from the generated narrative,
then flags any that do not appear in the source evidence JSON or the officer's
free-text summary. These are candidate hallucinations the officer must review.

This is intentionally conservative (prefers false-positive warnings over
missing real hallucinations) and uses only regex + simple heuristics, not
an external NER model — so it runs offline with zero latency overhead.
"""

from __future__ import annotations

import json
import re
from typing import Any


# ─── Claim extractors ─────────────────────────────────────────────────────────

# Dates: "2026-07-01", "01 July 2026", "July 1, 2026", "01/07/2026"
_DATE_PATTERNS: list[str] = [
    r"\b\d{4}-\d{2}-\d{2}\b",                               # ISO: 2026-07-01
    r"\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{4}\b",                                           # DD Month YYYY
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},?\s+\d{4}\b",                              # Month DD, YYYY
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",                           # DD/MM/YYYY
]

# Rupee amounts: "₹50,000", "Rs. 2,00,000", "50000 rupees", "2 lakh"
_AMOUNT_PATTERNS: list[str] = [
    r"(?:₹|Rs\.?)\s*[\d,]+(?:\.\d+)?",
    r"\b[\d,]+(?:\.\d+)?\s*(?:rupees?|lakh|crore)\b",
    r"\bINR\s*[\d,]+",
]

# Proper nouns: Capitalised sequences (Title Case, 2–4 words, not sentence starts)
_PROPER_NOUN_PATTERN = re.compile(
    r"(?<![.!?]\s)(?<!\n)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})"
)

# Common generic words to exclude from proper noun checks
_PROPER_NOUN_STOPWORDS = frozenset({
    "The", "This", "These", "That", "Those", "On", "In", "At", "An", "To",
    "By", "Of", "Or", "And", "But", "If", "It", "He", "She", "We", "Our",
    "Your", "Their", "They", "You", "His", "Her", "Its", "With", "From",
    "For", "As", "Is", "Was", "Are", "Were", "Be", "Been", "Have", "Had",
    "Has", "Do", "Did", "Does", "Not", "No", "New", "Next",
    # FIR-specific legal boilerplate to ignore
    "Bharatiya Nyaya Sanhita", "Information Technology", "High Risk",
    "Audit Log", "Cyber Crime", "National Cyber", "TO BE CONFIRMED",
    "Evidence Appendix", "Draft Status", "Generated Officer",
})


def _extract_dates(text: str) -> list[str]:
    hits: list[str] = []
    for pat in _DATE_PATTERNS:
        hits.extend(re.findall(pat, text, flags=re.IGNORECASE))
    return list(dict.fromkeys(hits))  # de-dupe, preserve order


def _extract_amounts(text: str) -> list[str]:
    hits: list[str] = []
    for pat in _AMOUNT_PATTERNS:
        hits.extend(re.findall(pat, text, flags=re.IGNORECASE))
    return list(dict.fromkeys(hits))


def _extract_proper_nouns(text: str) -> list[str]:
    candidates = _PROPER_NOUN_PATTERN.findall(text)
    return [
        c for c in dict.fromkeys(candidates)
        if c not in _PROPER_NOUN_STOPWORDS and len(c.split()) <= 4
    ]


def extract_claims(narrative: str) -> dict[str, list[str]]:
    """Extract all verifiable claims from the narrative."""
    return {
        "dates": _extract_dates(narrative),
        "amounts": _extract_amounts(narrative),
        "proper_nouns": _extract_proper_nouns(narrative),
    }


def _build_evidence_corpus(evidence_items: list[Any], officer_summary: str | None) -> str:
    """Flatten all evidence into a single searchable string."""
    parts: list[str] = []
    if officer_summary:
        parts.append(officer_summary)
    for item in evidence_items:
        # Include the event_id so it never flags the citation line as ungrounded
        parts.append(item.event_id)
        parts.append(item.timestamp.isoformat() if hasattr(item.timestamp, "isoformat") else str(item.timestamp))
        parts.append(item.module_name if isinstance(item.module_name, str) else item.module_name.value)
        parts.append(json.dumps(item.decision_output, default=str))
        if item.review_action:
            parts.append(item.review_action)
        if item.human_reviewer:
            parts.append(item.human_reviewer)
    return " ".join(parts).lower()


def check_grounding(
    narrative: str,
    evidence_items: list[Any],
    officer_summary: str | None = None,
) -> list[str]:
    """
    Returns a list of grounding warning strings.
    Each warning names a specific claim from the narrative that could not be
    found in the evidence or officer summary.

    An empty list means the grounding check passed (no candidate hallucinations).
    """
    corpus = _build_evidence_corpus(evidence_items, officer_summary)
    claims = extract_claims(narrative)
    warnings: list[str] = []

    for date in claims["dates"]:
        # Normalize separators for comparison
        normalized = re.sub(r"[\s/,-]+", "", date.lower())
        if normalized not in re.sub(r"[\s/,-]+", "", corpus):
            warnings.append(
                f'Date "{date}" appears in the narrative but was not found in the source evidence. '
                "Confirm or remove before filing."
            )

    for amount in claims["amounts"]:
        normalized = re.sub(r"[\s,₹]", "", amount.lower().replace("rs.", "").replace("rs", ""))
        if normalized and normalized not in re.sub(r"[\s,₹]", "", corpus.lower().replace("rs.", "").replace("rs", "")):
            warnings.append(
                f'Amount "{amount}" appears in the narrative but was not found in the source evidence. '
                "Confirm or remove before filing."
            )

    for noun in claims["proper_nouns"]:
        if noun.lower() not in corpus:
            warnings.append(
                f'Name/entity "{noun}" appears in the narrative but was not found in the source evidence. '
                "Confirm or remove before filing."
            )

    return warnings

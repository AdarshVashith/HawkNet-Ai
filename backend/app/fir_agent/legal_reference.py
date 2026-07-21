"""
Illustrative pattern-to-law-section reference table.

IMPORTANT — READ BEFORE USING:
This module is a STARTING-POINT LOOKUP, not a legal authority. Section
numbers and applicability change with amendments, case law, and the
specific facts of a case, and India's criminal code changed from the
Indian Penal Code (IPC) to the Bharatiya Nyaya Sanhita (BNS) in July 2024.
Every entry here MUST be verified by a qualified legal officer / public
prosecutor against the current text of the law before it appears in any
document that is actually filed. Treat every "section" value below as
"a section worth checking," never as a citation you can rely on as-is.

This is deliberately conservative: the drafting agent should always mark
suggested_sections[].verified_by_officer = False until a human confirms.
"""

from __future__ import annotations

from typing import NamedTuple


class PatternMapping(NamedTuple):
    pattern_key: str
    plain_description: str
    candidate_acts_and_sections: list[str]   # human-readable "act + section" strings
    verify_note: str


# NOTE: candidate_acts_and_sections below list COMMONLY-DISCUSSED sections in
# public legal commentary on cyber fraud / impersonation-based cheating in
# India as of early 2026. They are provided so an officer has a fast starting
# checklist, not so the system can auto-cite them. CONFIRM AGAINST CURRENT LAW.
PATTERN_LIBRARY: list[PatternMapping] = [
    PatternMapping(
        pattern_key="digital_arrest_impersonation",
        plain_description=(
            "Caller impersonated a government/law-enforcement official (e.g. "
            "police, CBI, ED, Customs) to coerce a victim into transferring money "
            "or staying on a video call under threat of arrest."
        ),
        candidate_acts_and_sections=[
            "Bharatiya Nyaya Sanhita, 2023 — cheating-related provisions (successor to former IPC 420)",
            "Bharatiya Nyaya Sanhita, 2023 — personation of a public servant (successor to former IPC 419)",
            "Bharatiya Nyaya Sanhita, 2023 — criminal intimidation provisions (successor to former IPC 503/506)",
            "Information Technology Act, 2000 — Section 66C (identity theft)",
            "Information Technology Act, 2000 — Section 66D (cheating by personation using a computer resource)",
        ],
        verify_note=(
            "Exact BNS section numbers replacing IPC 419/420/503/506 must be confirmed; "
            "do not rely on this list's numbering without checking the current bare act."
        ),
    ),
    PatternMapping(
        pattern_key="counterfeit_currency_possession_or_use",
        plain_description=(
            "Possession, circulation, or use of counterfeit currency notes."
        ),
        candidate_acts_and_sections=[
            "Bharatiya Nyaya Sanhita, 2023 — provisions on counterfeit currency (successor to former IPC Sections 489A–489E)",
        ],
        verify_note=(
            "Confirm current BNS numbering and whether the note qualifies as "
            "'counterfeit' vs 'forged/altered' under the current statutory definition."
        ),
    ),
    PatternMapping(
        pattern_key="online_financial_fraud_mule_network",
        plain_description=(
            "Coordinated fund transfers through intermediary ('mule') bank "
            "accounts to launder proceeds of an online fraud."
        ),
        candidate_acts_and_sections=[
            "Bharatiya Nyaya Sanhita, 2023 — cheating and criminal breach of trust provisions",
            "Prevention of Money Laundering Act, 2002 — as applicable, for referral to ED",
            "Information Technology Act, 2000 — Section 66D",
        ],
        verify_note=(
            "PMLA applicability generally requires a predicate offence and a "
            "financial-intelligence threshold — confirm with a legal officer "
            "whether referral is appropriate before including it in a filing."
        ),
    ),
    PatternMapping(
        pattern_key="geospatial_hotspot_fraud",
        plain_description=(
            "Geospatial analysis identified the reported incident location as a known "
            "high-risk fraud hotspot with multiple clustered incidents."
        ),
        candidate_acts_and_sections=[
            "Bharatiya Nyaya Sanhita, 2023 — cheating provisions (pattern of organized deception)",
            "Information Technology Act, 2000 — Section 66D",
        ],
        verify_note=(
            "Geospatial risk scores are probabilistic indicators, not evidence of specific "
            "offences. Confirm the actual incident details match the alleged section."
        ),
    ),
]


def lookup(pattern_key: str) -> PatternMapping | None:
    for entry in PATTERN_LIBRARY:
        if entry.pattern_key == pattern_key:
            return entry
    return None


DISCLAIMER_TEXT = (
    "Suggested sections in this document are AI-generated starting points based on "
    "publicly discussed legal patterns, not a legal determination. They must be "
    "independently verified against the current Bharatiya Nyaya Sanhita, Information "
    "Technology Act, and any applicable special statutes by a qualified legal officer "
    "before this document is used in any filing."
)

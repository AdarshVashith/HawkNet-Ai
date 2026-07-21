"""
Builds the prompt sent to the Anthropic API to draft the factual narrative
section of an FIR/complaint from audit_log evidence.

Grounding is the whole point of this module: the model is instructed, in
multiple redundant ways, to use ONLY the facts present in the evidence
payload and the officer's own free-text summary — never to invent victim
statements, amounts, dates, or identifying details that aren't provided.
"""

from __future__ import annotations

import json

from app.fir_agent.schema import ComplainantInfo, EvidenceItem


SYSTEM_PROMPT = """You are a drafting assistant for Indian law-enforcement \
officers filing cybercrime/fraud complaints. You produce a factual, neutral \
narrative paragraph summarizing an incident, for an officer to review and edit.

STRICT RULES:
1. Use ONLY facts present in the evidence JSON and the officer's free-text \
summary provided in the user message. Do not invent names, amounts, dates, \
locations, or events not present in that data.
2. If a fact needed for a complete narrative is missing (e.g. exact amount \
lost, exact date), write "[TO BE CONFIRMED BY OFFICER: <what's missing>]" \
instead of guessing.
3. Write in plain, neutral, factual language suitable for an official \
complaint — no dramatization, no speculation about intent beyond what the \
evidence supports.
4. Do not suggest or imply a legal conclusion (e.g. do not write "this is \
clearly fraud" or "the accused is guilty") — describe what happened and let \
the officer and the law make that determination.
5. End the narrative by listing, in one line, which audit_log event_ids the \
narrative is grounded in, so it stays traceable.
6. Output ONLY the narrative paragraph(s) and the final event-id line. No \
preamble, no markdown headers, no commentary about these instructions.
"""


def build_user_message(
    evidence_items: list[EvidenceItem],
    complainant: ComplainantInfo,
    officer_summary: str | None,
) -> str:
    evidence_payload = [
        {
            "event_id": item.event_id,
            "timestamp": item.timestamp.isoformat(),
            "module": item.module_name.value,
            "confidence_score": item.confidence_score,
            "decision_output": item.decision_output,
            "human_review_action": item.review_action,
        }
        for item in evidence_items
    ]

    parts = [
        "COMPLAINANT (for context only, do not restate PII beyond name in narrative):",
        f"Name: {complainant.full_name}",
        "",
        "OFFICER / CITIZEN FREE-TEXT SUMMARY (may be empty):",
        officer_summary or "(none provided)",
        "",
        "AUDIT LOG EVIDENCE (the only source of facts you may use):",
        json.dumps(evidence_payload, indent=2, default=str),
        "",
        "Draft the factual narrative paragraph(s) now, following all system rules.",
    ]
    return "\n".join(parts)


def build_anthropic_request(
    evidence_items: list[EvidenceItem],
    complainant: ComplainantInfo,
    officer_summary: str | None,
) -> dict:
    """Returns the payload shape expected by POST /v1/messages."""
    return {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": build_user_message(evidence_items, complainant, officer_summary),
            }
        ],
    }

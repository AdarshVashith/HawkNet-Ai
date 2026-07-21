"""
API layer for the Evidence-to-FIR Drafting Agent.

Endpoints:
  POST /api/fir-agent/draft              -> generate a new draft from evidence
  PATCH /api/fir-agent/draft/{id}/review -> officer records edits/approval
  GET  /api/fir-agent/draft/{id}         -> fetch a draft by ID
  GET  /api/fir-agent/draft/{id}/export  -> render current draft to .docx
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.fir_agent.grounding_check import check_grounding
from app.fir_agent.legal_reference import lookup as legal_lookup
from app.fir_agent.prompt_builder import build_anthropic_request
from app.fir_agent.schema import (
    DraftStatus,
    EvidenceItem,
    FIRDraft,
    FIRDraftRequest,
    SourceModule,
    SuggestedLegalSection,
)
from db.session import get_db

router = APIRouter(prefix="/api/fir-agent", tags=["fir-agent"])

# ---------------------------------------------------------------------------
# In-memory draft store (sufficient for demo; swap for DB-backed store in prod)
# ---------------------------------------------------------------------------
_DRAFTS: dict[str, FIRDraft] = {}


# ---------------------------------------------------------------------------
# Prompt 11.2 — Real DB query replacing the in-memory stub
# ---------------------------------------------------------------------------

def get_audit_log_items(db: Session, event_ids: list[str]) -> list[EvidenceItem]:
    """
    Fetch AiAuditLog rows from the real SQLite DB and map them to EvidenceItem.
    Raises HTTP 404 with a clear per-event message for any missing event_id.
    """
    from db.models import AiAuditLog
    from sqlalchemy import select

    items: list[EvidenceItem] = []
    for eid in event_ids:
        row = db.scalar(select(AiAuditLog).where(AiAuditLog.event_id == eid))
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"audit_log event_id not found: {eid}. "
                       f"Run an analysis module first to generate audit records.",
            )
        # Parse decision_output JSON
        try:
            decision_output = json.loads(row.decision_output)
        except (json.JSONDecodeError, TypeError):
            decision_output = {"raw": row.decision_output}

        # Map module_name string -> SourceModule enum (graceful fallback)
        try:
            module_enum = SourceModule(row.module_name)
        except ValueError:
            module_enum = SourceModule.scam_detection  # fallback for unknown modules

        items.append(
            EvidenceItem(
                event_id=row.event_id,
                timestamp=datetime.fromisoformat(row.timestamp.replace("Z", "+00:00")),
                module_name=module_enum,
                input_reference=row.input_reference,
                model_version=row.model_version,
                confidence_score=row.confidence_score,
                decision_output=decision_output,
                human_reviewer=row.human_reviewer,
                review_action=row.review_action,
            )
        )
    return items


# ---------------------------------------------------------------------------
# Chain reference
# ---------------------------------------------------------------------------

def compute_chain_ref(evidence_items: list[EvidenceItem]) -> str:
    """Hash the ordered evidence event_ids + input_reference hashes so
    this draft is cryptographically linked to the exact audit trail."""
    payload = "|".join(f"{i.event_id}:{i.input_reference}" for i in evidence_items)
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Legal section suggestions
# ---------------------------------------------------------------------------

def suggest_sections_for_modules(evidence_items: list[EvidenceItem]) -> list[SuggestedLegalSection]:
    """Heuristic mapping from module -> candidate pattern key.
    Deliberately conservative — always unverified by default."""
    pattern_by_module = {
        "scam_detection": "digital_arrest_impersonation",
        "counterfeit": "counterfeit_currency_possession_or_use",
        "counterfeit_currency": "counterfeit_currency_possession_or_use",
        "fraud_graph": "online_financial_fraud_mule_network",
        "geospatial": "geospatial_hotspot_fraud",
    }
    suggestions: list[SuggestedLegalSection] = []
    seen_patterns: set[str] = set()
    for item in evidence_items:
        module_val = item.module_name.value if hasattr(item.module_name, "value") else str(item.module_name)
        pattern_key = pattern_by_module.get(module_val)
        if not pattern_key or pattern_key in seen_patterns:
            continue
        seen_patterns.add(pattern_key)
        mapping = legal_lookup(pattern_key)
        if not mapping:
            continue
        for act_section in mapping.candidate_acts_and_sections:
            act, _, section = act_section.partition(" — ")
            suggestions.append(
                SuggestedLegalSection(
                    act=act.strip(),
                    section=section.strip() or "(see plain_language_basis)",
                    plain_language_basis=f"{mapping.plain_description} {mapping.verify_note}",
                    verified_by_officer=False,
                )
            )
    return suggestions


# ---------------------------------------------------------------------------
# Narrative generation (Anthropic API)
# ---------------------------------------------------------------------------

async def call_anthropic_for_narrative(
    evidence_items: list[EvidenceItem],
    complainant,
    officer_summary: str | None,
) -> str:
    """Calls the Anthropic API to draft the grounded narrative.
    Set ANTHROPIC_API_KEY env variable to enable. Falls back to a structured
    placeholder if no key is configured, so the tool is still usable offline."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Structured offline placeholder so the UI is still fully exercisable
        event_ids = ", ".join(i.event_id for i in evidence_items)
        modules = ", ".join(set(i.module_name.value for i in evidence_items))
        return (
            f"[DRAFT NARRATIVE — AI GENERATION REQUIRES ANTHROPIC_API_KEY]\n\n"
            f"Based on the audit log evidence records, this complaint concerns an incident "
            f"detected by the following AI modules: {modules}. "
            f"The AI system flagged the following events with high confidence scores "
            f"indicating potential fraudulent activity: {event_ids}.\n\n"
            f"[TO BE CONFIRMED BY OFFICER: Exact incident date, victim statement, "
            f"financial loss amount, and accused details must be entered by the investigating officer.]\n\n"
            f"Grounded in audit_log event_ids: {event_ids}"
        )

    request_payload = build_anthropic_request(evidence_items, complainant, officer_summary)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=request_payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        resp.raise_for_status()
        data = resp.json()
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    return "\n".join(text_blocks).strip()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/draft", response_model=FIRDraft)
async def create_draft(
    req: FIRDraftRequest,
    db: Annotated[Session, Depends(get_db)],
) -> FIRDraft:
    """Generate a new FIR draft from selected audit log evidence events."""
    evidence_items = get_audit_log_items(db, req.evidence_event_ids)
    if not evidence_items:
        raise HTTPException(status_code=400, detail="No evidence items resolved.")

    narrative = await call_anthropic_for_narrative(
        evidence_items, req.complainant, req.incident_summary_by_officer
    )

    # Prompt 11.4 — run grounding check immediately after generation
    grounding_warnings = check_grounding(
        narrative, evidence_items, req.incident_summary_by_officer
    )

    suggested_sections = suggest_sections_for_modules(evidence_items)
    chain_ref = compute_chain_ref(evidence_items)

    draft = FIRDraft(
        draft_id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        status=DraftStatus.generated,
        complainant=req.complainant,
        evidence_items=evidence_items,
        narrative=narrative,
        suggested_sections=suggested_sections,
        grounding_warnings=grounding_warnings,
        jurisdiction_police_station=req.jurisdiction_police_station,
        jurisdiction_state=req.jurisdiction_state,
        audit_chain_ref=chain_ref,
    )
    _DRAFTS[draft.draft_id] = draft
    return draft


class ReviewUpdate(BaseModel):
    status: DraftStatus
    edited_narrative: str | None = None
    verified_section_indexes: list[int] = []
    officer_name: str


@router.patch("/draft/{draft_id}/review", response_model=FIRDraft)
def review_draft(draft_id: str, update: ReviewUpdate) -> FIRDraft:
    """Officer records edits, verifies law sections, and updates status."""
    draft = _DRAFTS.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found.")

    if update.edited_narrative is not None:
        # Re-run grounding check on the edited narrative
        new_warnings = check_grounding(
            update.edited_narrative,
            draft.evidence_items,
            None,
        )
        draft = draft.model_copy(update={
            "narrative": update.edited_narrative,
            "grounding_warnings": new_warnings,
        })

    # Mark verified sections
    sections = [s.model_copy() for s in draft.suggested_sections]
    for idx in update.verified_section_indexes:
        if 0 <= idx < len(sections):
            sections[idx] = sections[idx].model_copy(update={"verified_by_officer": True})

    draft = draft.model_copy(update={
        "suggested_sections": sections,
        "status": update.status,
    })
    _DRAFTS[draft_id] = draft
    return draft


@router.get("/draft/{draft_id}", response_model=FIRDraft)
def get_draft(draft_id: str) -> FIRDraft:
    """Fetch a draft by ID."""
    draft = _DRAFTS.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return draft


@router.get("/draft/{draft_id}/export")
def export_draft(draft_id: str):
    """Render the current draft to a .docx file and return it for download."""
    from app.fir_agent.render import render_fir_draft_docx

    draft = _DRAFTS.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found.")

    out_path = os.path.join(tempfile.gettempdir(), f"fir_draft_{draft_id}.docx")
    render_fir_draft_docx(draft, out_path)
    return FileResponse(
        out_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"fir_draft_{draft.status.value}_{draft_id[:8]}.docx",
    )

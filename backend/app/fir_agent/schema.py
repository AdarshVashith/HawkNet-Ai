"""
Data models for the Evidence-to-FIR Drafting Agent.

Design intent: this agent NEVER files anything automatically. It converts
an existing, already-logged audit_log evidence trail (from the scam
detection / counterfeit / fraud-graph modules) into a structured DRAFT
complaint document. A human officer must review, correct, and approve
before it becomes an actual filed FIR / NCRB complaint.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceModule(str, Enum):
    scam_detection = "scam_detection"
    counterfeit = "counterfeit"
    fraud_graph = "fraud_graph"
    geospatial = "geospatial"
    citizen_shield = "citizen_shield"
    human_review = "human_review"


class DraftStatus(str, Enum):
    generated = "generated"           # AI produced it, no human has looked yet
    officer_reviewed = "officer_reviewed"  # a human edited/approved the content
    filed = "filed"                   # officer confirms it was actually submitted
    rejected = "rejected"             # officer discarded it as inaccurate/unusable


class EvidenceItem(BaseModel):
    """One entry pulled from the shared audit_log service.
    This is the ONLY source of facts the drafting agent is allowed to use —
    it must not invent details beyond this."""

    event_id: str
    timestamp: datetime
    module_name: SourceModule
    input_reference: str = Field(..., description="hash of the original input, not raw PII")
    model_version: str
    confidence_score: float
    decision_output: dict[str, Any]
    human_reviewer: Optional[str] = None
    review_action: Optional[str] = None


class ComplainantInfo(BaseModel):
    """Supplied by the officer/citizen at draft time — never inferred by
    the model. Keep this separate from EvidenceItem so PII is only ever
    entered by a human, deliberately, at the point of filing."""

    full_name: str
    contact_number: str
    address: Optional[str] = None
    id_proof_type: Optional[str] = None
    id_proof_number_last4: Optional[str] = None  # store only last 4 digits


class FIRDraftRequest(BaseModel):
    complainant: ComplainantInfo
    evidence_event_ids: list[str] = Field(
        ..., description="one or more audit_log event_ids to build the complaint from"
    )
    incident_summary_by_officer: Optional[str] = Field(
        None,
        description=(
            "optional free-text the officer/citizen provides describing what "
            "happened in their own words; the agent will incorporate but not "
            "override this with invented narrative"
        ),
    )
    jurisdiction_police_station: Optional[str] = None
    jurisdiction_state: Optional[str] = None


class SuggestedLegalSection(BaseModel):
    """A candidate law section the drafting agent thinks may apply, with an
    explicit verification flag. NEVER presented as a final legal determination —
    see legal_reference.py for the disclaimer this is bound to."""

    act: str                   # e.g. "Bharatiya Nyaya Sanhita, 2023" or "IT Act, 2000"
    section: str               # e.g. "318(4)"
    plain_language_basis: str  # why the agent suggests it, in plain English
    verified_by_officer: bool = False


class FIRDraft(BaseModel):
    draft_id: str
    created_at: datetime
    status: DraftStatus = DraftStatus.generated
    complainant: ComplainantInfo
    evidence_items: list[EvidenceItem]
    narrative: str = Field(
        ..., description="drafted factual narrative, grounded only in evidence_items"
    )
    suggested_sections: list[SuggestedLegalSection]
    grounding_warnings: list[str] = Field(
        default_factory=list,
        description="candidate hallucinations flagged by grounding check — officer should review",
    )
    total_estimated_loss: Optional[float] = None
    jurisdiction_police_station: Optional[str] = None
    jurisdiction_state: Optional[str] = None
    audit_chain_ref: str = Field(
        ..., description="hash linking this draft back into the audit_log chain"
    )
    disclaimer: str = (
        "This is an AI-generated DRAFT for investigating-officer review only. "
        "It is not a filed legal document and creates no legal effect until an "
        "authorized officer reviews, corrects, and files it through proper channels. "
        "Suggested law sections are illustrative starting points, not legal "
        "determinations, and must be independently verified."
    )

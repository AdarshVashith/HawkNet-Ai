import { useState } from 'react'
import type {
  AuditEvent,
  ComplainantInfo,
  FIRDraft,
  FIRDraftRequest,
  FIRReviewUpdate,
  SuggestedLegalSection,
} from '../lib/api'
import { createFIRDraft, reviewFIRDraft, exportFIRDraft } from '../lib/api'

interface Props {
  selectedEvents: AuditEvent[]
  onClose: () => void
}

type Step = 'complainant' | 'review'

const DRAFT_STATUS_LABELS: Record<FIRDraft['status'], string> = {
  generated: 'Generated',
  officer_reviewed: 'Officer Reviewed',
  filed: 'Filed',
  rejected: 'Rejected',
}

const DRAFT_STATUS_COLORS: Record<FIRDraft['status'], string> = {
  generated: '#f59e0b',
  officer_reviewed: '#3b82f6',
  filed: '#10b981',
  rejected: '#f43f5e',
}

function StatusPill({ status }: { status: FIRDraft['status'] }) {
  return (
    <span style={{
      padding: '0.25rem 0.75rem',
      borderRadius: 20,
      fontSize: '0.75rem',
      fontWeight: 700,
      letterSpacing: '0.06em',
      textTransform: 'uppercase',
      background: DRAFT_STATUS_COLORS[status] + '22',
      color: DRAFT_STATUS_COLORS[status],
      border: `1px solid ${DRAFT_STATUS_COLORS[status]}55`,
    }}>
      {DRAFT_STATUS_LABELS[status]}
    </span>
  )
}

function DraftBanner({ status }: { status: FIRDraft['status'] }) {
  return (
    <div style={{
      background: '#b00000',
      color: '#ffffff',
      textAlign: 'center',
      padding: '0.6rem 1rem',
      fontWeight: 800,
      fontSize: '0.9rem',
      letterSpacing: '0.12em',
      textTransform: 'uppercase',
      borderRadius: '8px 8px 0 0',
      flexShrink: 0,
    }}>
      DRAFT — {status.toUpperCase().replace(/_/g, ' ')} — NOT A FILED LEGAL DOCUMENT
    </div>
  )
}

export default function FIRDraftModal({ selectedEvents, onClose }: Props) {
  const [step, setStep] = useState<Step>('complainant')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState<FIRDraft | null>(null)
  const [exportBusy, setExportBusy] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  // Complainant form
  const [fullName, setFullName] = useState('')
  const [contact, setContact] = useState('')
  const [address, setAddress] = useState('')
  const [policeStation, setPoliceStation] = useState('')
  const [state, setState] = useState('')
  const [officerSummary, setOfficerSummary] = useState('')
  const [officerName, setOfficerName] = useState('')

  // Review form
  const [narrative, setNarrative] = useState('')
  const [verifiedSections, setVerifiedSections] = useState<Set<number>>(new Set())

  const allSectionsVerified =
    draft !== null &&
    draft.suggested_sections.length > 0 &&
    draft.suggested_sections.every((_, i) => verifiedSections.has(i))

  async function handleCreateDraft() {
    if (!fullName.trim() || !contact.trim()) {
      setError('Complainant name and contact number are required.')
      return
    }
    setError(null)
    setBusy(true)
    try {
      const complainant: ComplainantInfo = {
        full_name: fullName.trim(),
        contact_number: contact.trim(),
        address: address.trim() || undefined,
      }
      const req: FIRDraftRequest = {
        complainant,
        evidence_event_ids: selectedEvents.map(e => e.event_id),
        incident_summary_by_officer: officerSummary.trim() || undefined,
        jurisdiction_police_station: policeStation.trim() || undefined,
        jurisdiction_state: state.trim() || undefined,
      }
      const result = await createFIRDraft(req)
      setDraft(result)
      setNarrative(result.narrative)
      setStep('review')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate draft.')
    } finally {
      setBusy(false)
    }
  }

  async function handleSaveReview(newStatus: FIRDraft['status']) {
    if (!draft) return
    setError(null)
    setBusy(true)
    try {
      const update: FIRReviewUpdate = {
        status: newStatus,
        edited_narrative: narrative !== draft.narrative ? narrative : undefined,
        verified_section_indexes: Array.from(verifiedSections),
        officer_name: officerName.trim() || 'Duty Officer',
      }
      const updated = await reviewFIRDraft(draft.draft_id, update)
      setDraft(updated)
      setNarrative(updated.narrative)
      setSaveMessage('Review saved successfully.')
      setTimeout(() => setSaveMessage(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save review.')
    } finally {
      setBusy(false)
    }
  }

  async function handleExport() {
    if (!draft) return
    setExportBusy(true)
    setError(null)
    try {
      const filename = `FIR_Draft_${draft.status}_${draft.draft_id.slice(0, 8)}.docx`
      await exportFIRDraft(draft.draft_id, filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed.')
    } finally {
      setExportBusy(false)
    }
  }

  function toggleSection(idx: number) {
    setVerifiedSections(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.75)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '1.5rem',
      backdropFilter: 'blur(4px)',
    }}>
      <div style={{
        width: '100%', maxWidth: 900,
        maxHeight: '90vh',
        display: 'flex', flexDirection: 'column',
        background: 'var(--card-bg)',
        borderRadius: 10,
        border: '1px solid var(--border-default)',
        overflow: 'hidden',
        boxShadow: '0 25px 60px rgba(0,0,0,0.5)',
      }}>

        {/* Red DRAFT Banner — always visible */}
        {draft && <DraftBanner status={draft.status} />}

        {/* Modal Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '1rem 1.4rem',
          borderBottom: '1px solid var(--border-default)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                FIR / Complaint Draft — Evidence-to-Complaint Agent
              </h2>
              <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>
                {selectedEvents.length} audit event{selectedEvents.length !== 1 ? 's' : ''} selected
                {draft && <> &nbsp;·&nbsp; Draft ID: <code style={{ fontSize: '0.72rem' }}>{draft.draft_id.slice(0, 16)}…</code></>}
              </p>
            </div>
            {draft && <StatusPill status={draft.status} />}
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', fontSize: '1.4rem', lineHeight: 1,
              padding: '0.25rem 0.5rem',
            }}
          >
            ×
          </button>
        </div>

        {/* Step Tabs */}
        <div style={{
          display: 'flex', gap: 0,
          borderBottom: '1px solid var(--border-default)',
          flexShrink: 0,
        }}>
          {(['complainant', 'review'] as Step[]).map((s, i) => (
            <button
              key={s}
              type="button"
              onClick={() => { if (draft || s === 'complainant') setStep(s) }}
              style={{
                flex: 1, padding: '0.6rem', fontSize: '0.82rem',
                fontWeight: step === s ? 700 : 400,
                background: step === s ? 'var(--bg-elevated)' : 'transparent',
                color: step === s ? 'var(--text-primary)' : 'var(--text-muted)',
                border: 'none',
                borderBottom: step === s ? '2px solid #3b82f6' : '2px solid transparent',
                cursor: draft || s === 'complainant' ? 'pointer' : 'not-allowed',
                opacity: !draft && s === 'review' ? 0.4 : 1,
              }}
            >
              {i + 1}. {s === 'complainant' ? 'Complainant & Context' : 'Review Draft & Export'}
            </button>
          ))}
        </div>

        {/* Scrollable Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.4rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

          {error && (
            <div style={{
              padding: '0.75rem 1rem',
              background: '#f43f5e18', border: '1px solid #f43f5e55',
              borderRadius: 8, color: '#f43f5e', fontSize: '0.85rem',
            }}>
              {error}
            </div>
          )}

          {saveMessage && (
            <div style={{
              padding: '0.6rem 1rem',
              background: '#10b98118', border: '1px solid #10b98155',
              borderRadius: 8, color: '#10b981', fontSize: '0.82rem',
            }}>
              {saveMessage}
            </div>
          )}

          {/* ── STEP 1: Complainant ───────────────────────────────── */}
          {step === 'complainant' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>

              {/* Selected Evidence Preview */}
              <div className="glass-card" style={{ padding: '1rem', borderRadius: 8 }}>
                <h3 style={{ margin: '0 0 0.75rem', fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Evidence Events Selected
                </h3>
                <table className="data-table" style={{ fontSize: '0.8rem' }}>
                  <thead>
                    <tr>
                      <th>Event ID</th>
                      <th>Module</th>
                      <th>AI Confidence</th>
                      <th>Officer Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedEvents.map(ev => (
                      <tr key={ev.event_id}>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.72rem' }}>{ev.event_id.slice(0, 20)}…</td>
                        <td>{ev.module_name.replace(/_/g, ' ')}</td>
                        <td style={{ fontWeight: 700, color: '#10b981' }}>{Math.round(ev.confidence_score * 100)}%</td>
                        <td style={{ textTransform: 'uppercase', fontSize: '0.72rem' }}>{ev.review_action || 'pending'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Complainant Fields */}
              <div className="glass-card" style={{ padding: '1rem', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
                <h3 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Complainant Details
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="section-label" htmlFor="fir-name">Full Name *</label>
                    <input
                      id="fir-name"
                      className="input-field"
                      value={fullName}
                      onChange={e => setFullName(e.target.value)}
                      placeholder="As per government ID"
                      style={{ borderRadius: 8 }}
                    />
                  </div>
                  <div>
                    <label className="section-label" htmlFor="fir-contact">Contact Number *</label>
                    <input
                      id="fir-contact"
                      className="input-field"
                      value={contact}
                      onChange={e => setContact(e.target.value)}
                      placeholder="+91 XXXXXXXXXX"
                      style={{ borderRadius: 8 }}
                    />
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <label className="section-label" htmlFor="fir-address">Address (optional)</label>
                    <input
                      id="fir-address"
                      className="input-field"
                      value={address}
                      onChange={e => setAddress(e.target.value)}
                      placeholder="Full postal address"
                      style={{ borderRadius: 8 }}
                    />
                  </div>
                </div>
              </div>

              {/* Jurisdiction */}
              <div className="glass-card" style={{ padding: '1rem', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
                <h3 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Jurisdiction & Officer Context
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="section-label" htmlFor="fir-ps">Police Station (optional)</label>
                    <input id="fir-ps" className="input-field" value={policeStation} onChange={e => setPoliceStation(e.target.value)} style={{ borderRadius: 8 }} />
                  </div>
                  <div>
                    <label className="section-label" htmlFor="fir-state">State (optional)</label>
                    <input id="fir-state" className="input-field" value={state} onChange={e => setState(e.target.value)} style={{ borderRadius: 8 }} />
                  </div>
                  <div style={{ gridColumn: '1 / -1' }}>
                    <label className="section-label" htmlFor="fir-summary">Officer Free-Text Summary (optional — will be used but not overridden by AI)</label>
                    <textarea
                      id="fir-summary"
                      className="input-field"
                      rows={3}
                      value={officerSummary}
                      onChange={e => setOfficerSummary(e.target.value)}
                      placeholder="Briefly describe what happened in your own words. The AI will incorporate this without inventing additional facts."
                      style={{ borderRadius: 8 }}
                    />
                  </div>
                </div>
              </div>

              <button
                type="button"
                className="btn-primary"
                onClick={handleCreateDraft}
                disabled={busy || !fullName.trim() || !contact.trim()}
                style={{ borderRadius: 8, minHeight: 42, fontWeight: 700 }}
              >
                {busy ? <span className="spinner" /> : 'Generate FIR Draft'}
              </button>
            </div>
          )}

          {/* ── STEP 2: Review Draft ──────────────────────────────── */}
          {step === 'review' && draft && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

              {/* Grounding Warnings */}
              {draft.grounding_warnings.length > 0 && (
                <div style={{
                  padding: '0.9rem 1rem',
                  background: '#f59e0b18', border: '1px solid #f59e0b55',
                  borderRadius: 8,
                }}>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#f59e0b', marginBottom: '0.5rem' }}>
                    Grounding Warnings — AI Hallucination Candidates
                  </div>
                  <p style={{ margin: '0 0 0.5rem', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    The following items appear in the AI narrative but could not be verified against the source evidence.
                    You MUST confirm or remove each before filing.
                  </p>
                  <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                    {draft.grounding_warnings.map((w, i) => (
                      <li key={i} style={{ fontSize: '0.8rem', color: '#fbbf24' }}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Editable Narrative */}
              <div className="glass-card" style={{ padding: '1rem', borderRadius: 8 }}>
                <h3 style={{ margin: '0 0 0.6rem', fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Factual Narrative
                  <span style={{ marginLeft: '0.5rem', fontSize: '0.72rem', fontWeight: 400, color: 'var(--text-muted)' }}>
                    AI-drafted — edit as needed before filing
                  </span>
                </h3>
                <textarea
                  id="fir-narrative"
                  className="input-field"
                  rows={8}
                  value={narrative}
                  onChange={e => setNarrative(e.target.value)}
                  style={{ borderRadius: 8, fontFamily: 'Georgia, serif', fontSize: '0.88rem', lineHeight: 1.6 }}
                />
              </div>

              {/* Law Sections */}
              <div className="glass-card" style={{ padding: '1rem', borderRadius: 8 }}>
                <h3 style={{ margin: '0 0 0.4rem', fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Suggested Law Sections
                  <span style={{ marginLeft: '0.5rem', fontSize: '0.72rem', fontWeight: 400, color: '#f59e0b' }}>
                    Tick each after independently verifying — Export is locked until all are verified
                  </span>
                </h3>
                <p style={{ margin: '0 0 0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  These are AI-suggested starting points only. Verify each against the current text of the law with a qualified legal officer before filing.
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {draft.suggested_sections.map((sec: SuggestedLegalSection, idx: number) => (
                    <div
                      key={idx}
                      style={{
                        padding: '0.75rem',
                        background: verifiedSections.has(idx) ? '#10b98110' : 'var(--bg-elevated)',
                        border: `1px solid ${verifiedSections.has(idx) ? '#10b98155' : 'var(--border-default)'}`,
                        borderRadius: 8,
                        display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <input
                        type="checkbox"
                        id={`sec-${idx}`}
                        checked={verifiedSections.has(idx)}
                        onChange={() => toggleSection(idx)}
                        style={{ marginTop: 3, cursor: 'pointer', width: 16, height: 16, accentColor: '#10b981', flexShrink: 0 }}
                      />
                      <label htmlFor={`sec-${idx}`} style={{ cursor: 'pointer', flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)', marginBottom: 2 }}>
                          {sec.act} — {sec.section}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                          {sec.plain_language_basis}
                        </div>
                        {verifiedSections.has(idx) && (
                          <div style={{ fontSize: '0.72rem', color: '#10b981', marginTop: 4, fontWeight: 700 }}>
                            Verified by officer
                          </div>
                        )}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              {/* Evidence Appendix */}
              <div className="glass-card" style={{ padding: '1rem', borderRadius: 8 }}>
                <h3 style={{ margin: '0 0 0.6rem', fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Evidence Appendix
                  <span style={{ marginLeft: '0.5rem', fontSize: '0.72rem', fontWeight: 400, color: 'var(--text-muted)' }}>
                    Audit Chain Ref: <code style={{ fontSize: '0.65rem' }}>{draft.audit_chain_ref.slice(0, 32)}…</code>
                  </span>
                </h3>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table" style={{ fontSize: '0.78rem' }}>
                    <thead>
                      <tr>
                        <th>Event ID</th>
                        <th>Timestamp</th>
                        <th>Module</th>
                        <th>Confidence</th>
                        <th>Review Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {draft.evidence_items.map(ev => (
                        <tr key={ev.event_id}>
                          <td style={{ fontFamily: 'monospace', fontSize: '0.68rem' }}>{ev.event_id.slice(0, 20)}…</td>
                          <td style={{ whiteSpace: 'nowrap' }}>{new Date(ev.timestamp).toLocaleString('en-IN')}</td>
                          <td>{ev.module_name.replace(/_/g, ' ')}</td>
                          <td style={{ fontWeight: 700, color: '#10b981' }}>{Math.round(ev.confidence_score * 100)}%</td>
                          <td style={{ textTransform: 'uppercase', fontSize: '0.72rem' }}>{ev.review_action || 'pending'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Disclaimer */}
              <div style={{
                padding: '0.75rem 1rem',
                background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
                borderRadius: 8, fontSize: '0.72rem', color: 'var(--text-muted)',
                fontStyle: 'italic', lineHeight: 1.6,
              }}>
                {draft.disclaimer}
              </div>

              {/* Officer Name + Action Row */}
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: '1 1 200px' }}>
                  <label className="section-label" htmlFor="fir-officer">Officer Name / Badge</label>
                  <input
                    id="fir-officer"
                    className="input-field"
                    value={officerName}
                    onChange={e => setOfficerName(e.target.value)}
                    placeholder="Duty Officer name (for records)"
                    style={{ borderRadius: 8 }}
                  />
                </div>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => handleSaveReview('officer_reviewed')}
                  disabled={busy}
                  style={{ borderRadius: 8, minHeight: 38, fontWeight: 400 }}
                >
                  {busy ? <span className="spinner" /> : 'Save Review'}
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleExport}
                  disabled={!allSectionsVerified || exportBusy}
                  title={!allSectionsVerified ? 'Verify all law sections before exporting' : 'Download .docx'}
                  style={{
                    borderRadius: 8, minHeight: 38, fontWeight: 700,
                    background: allSectionsVerified ? '#10b981' : undefined,
                    opacity: allSectionsVerified ? 1 : 0.5,
                    cursor: allSectionsVerified ? 'pointer' : 'not-allowed',
                  }}
                >
                  {exportBusy ? <span className="spinner" /> : 'Export .docx'}
                  {!allSectionsVerified && <span style={{ marginLeft: '0.4rem', fontSize: '0.72rem' }}>(verify sections first)</span>}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

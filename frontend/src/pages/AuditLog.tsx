import { Fragment, useEffect, useState } from 'react'
import {
  listAuditEvents,
  getAuditEvent,
  verifyAuditChain,
  reviewAuditEvent,
  getSection65BDossier,
  type AuditEvent,
  type Section65BDossier,
} from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import JsonViewer from '../components/JsonViewer'
import StatusDot from '../components/StatusDot'
import FIRDraftModal from './FIRDraftModal'

type AuditEventDetail = AuditEvent & {
  input_data?: unknown
  output_data?: unknown
  input_payload?: unknown
  decision_output?: unknown
  model_version?: string
  prev_event_hash?: string
  event_hash?: string
  human_reviewer?: string | null
}

type ChainVerify = {
  checked_count: number
  valid: boolean
  message: string
}

const PAGE_SIZE = 20
const MODULES = ['all', 'scam_detection', 'counterfeit', 'counterfeit_currency', 'fraud_graph', 'geospatial', 'citizen_shield']

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    })
  } catch {
    return ts
  }
}

function ModuleBadge({ name }: { name: string }) {
  const formatted =
    name === 'scam_detection' ? 'Scam Detection'
    : name === 'counterfeit' ? 'Counterfeit Listing'
    : name === 'counterfeit_currency' ? 'Currency Note Scan'
    : name === 'fraud_graph' ? 'Fraud Ring Analysis'
    : name === 'geospatial' ? 'Geospatial Intelligence'
    : name === 'citizen_shield' ? 'Citizen Shield Intake'
    : name.replace(/_/g, ' ')

  let color = '#a855f7'
  if (name.includes('scam')) color = '#f97316'
  else if (name.includes('currency')) color = '#eab308'
  else if (name.includes('counterfeit')) color = '#f59e0b'
  else if (name.includes('fraud')) color = '#3b82f6'
  else if (name.includes('geospatial')) color = '#10b981'

  return (
    <span style={{
      padding: '0.18rem 0.55rem',
      background: 'var(--bg-elevated)',
      border: '1px solid var(--border-default)',
      borderRadius: 6,
      fontSize: '0.75rem',
      fontWeight: 400,
      color: 'var(--text-primary)',
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.35rem',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
      {formatted}
    </span>
  )
}

function ConfidencePill({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 75 ? '#10b981' : pct >= 45 ? '#f59e0b' : '#f43f5e'

  return (
    <span style={{ fontSize: '0.8125rem', fontWeight: 700, color, display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
      {pct}%
    </span>
  )
}

function ReviewStatusCell({ action }: { action: string | null }) {
  if (!action || action === 'pending') {
    return (
      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 400, display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#f59e0b' }} />
        Pending Review
      </span>
    )
  }

  const isConfirm = action === 'confirm' || action === 'confirmed'
  const isEscalate = action === 'escalate' || action === 'escalated'
  const color = isConfirm ? '#10b981' : isEscalate ? '#f43f5e' : 'var(--text-secondary)'
  const icon = isConfirm ? '✓' : isEscalate ? '▲' : '•'

  return (
    <span style={{
      padding: '0.18rem 0.55rem', borderRadius: 6, fontSize: '0.75rem', fontWeight: 700,
      background: 'var(--bg-elevated)', color, border: `1px solid ${color}`,
      display: 'inline-flex', alignItems: 'center', gap: '0.35rem'
    }}>
      <span>{icon}</span>
      {action.toUpperCase()}
    </span>
  )
}

function IconShieldCheck() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 11 12 14 22 4"/>
    </svg>
  )
}

export default function AuditLog() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const [selectedModule, setSelectedModule] = useState('all')

  const [chain, setChain] = useState<ChainVerify | null>(null)
  const [chainLoading, setChainLoading] = useState(true)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<AuditEventDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [reviewSubmitting, setReviewSubmitting] = useState(false)

  const [dossierModal, setDossierModal] = useState<Section65BDossier | null>(null)
  const [dossierLoading, setDossierLoading] = useState(false)

  // FIR Draft selection
  const [selectedForFIR, setSelectedForFIR] = useState<Set<string>>(new Set())
  const [firModalOpen, setFirModalOpen] = useState(false)

  useEffect(() => {
    loadEvents(0)
    verifyAuditChain()
      .then(d => { setChain(d); setChainLoading(false) })
      .catch(() => setChainLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedModule])

  async function loadEvents(p: number) {
    setLoading(true); setError(null)
    try {
      const res = await listAuditEvents(p * PAGE_SIZE, PAGE_SIZE)
      const arr = Array.isArray(res?.events) ? res.events : Array.isArray(res) ? (res as AuditEvent[]) : []
      const total = typeof res?.total === 'number' ? res.total : arr.length
      
      const filtered = selectedModule === 'all' ? arr : arr.filter(e => e.module_name === selectedModule)

      if (p === 0) setEvents(filtered)
      else setEvents(prev => [...prev, ...filtered])
      
      setTotalCount(total)
      setPage(p)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit events')
    } finally {
      setLoading(false)
    }
  }

  async function openDetail(id: string) {
    if (selectedId === id) { setSelectedId(null); setDetail(null); return }
    setSelectedId(id)
    setDetail(null)
    setDetailLoading(true)
    try {
      const res = await getAuditEvent(id)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const rec = (res as any)?.record || res
      setDetail(rec as AuditEventDetail)
    } catch {
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  async function handleReview(eventId: string, action: 'confirm' | 'dismiss' | 'escalate') {
    setReviewSubmitting(true)
    try {
      await reviewAuditEvent(eventId, action, 'Duty Officer')
      await loadEvents(0)
      const freshChain = await verifyAuditChain()
      setChain(freshChain)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to record decision')
    } finally {
      setReviewSubmitting(false)
    }
  }

  async function openDossier(eventId: string) {
    setDossierLoading(true)
    try {
      const res = await getSection65BDossier(eventId)
      setDossierModal(res)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to load Section 65B Dossier')
    } finally {
      setDossierLoading(false)
    }
  }

  const pendingCount = events.filter(e => !e.review_action || e.review_action === 'pending').length
  const confirmedCount = events.filter(e => e.review_action === 'confirm' || e.review_action === 'confirmed').length
  const escalatedCount = events.filter(e => e.review_action === 'escalate' || e.review_action === 'escalated').length

  return (
    <div className="animate-fade-in" style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* ── Command Header & Legal Chain Status ───────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.85rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              Legal-Admissibility AI Decision Command Audit Log
            </h2>
            <RiskBadge level="low" label="Sec 65B Certified" />
          </div>
          <p style={{ margin: '0.2rem 0 0', color: 'var(--text-secondary)', fontSize: '0.8125rem', fontWeight: 400 }}>
            Tamper-evident SHA-256 hash-chained AI decision ledger for law enforcement & courtroom evidence admissibility.
          </p>
        </div>

        {chainLoading ? (
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>Verifying SHA-256 chain...</span>
        ) : chain ? (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.6rem',
            padding: '0.5rem 0.9rem',
            background: 'var(--bg-elevated)',
            border: `1px solid ${chain.valid ? '#10b981' : '#f43f5e'}`,
            borderRadius: 10,
          }}>
            <IconShieldCheck />
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: chain.valid ? '#10b981' : '#f43f5e', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <StatusDot status={chain.valid ? 'ok' : 'error'} />
                {chain.valid ? 'SHA-256 CHAIN INTACT & VALID' : 'TAMPER DETECTED IN CHAIN'}
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                {chain.checked_count} immutable records hash-verified from genesis block
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* ── KPI Command Cards ─────────────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: '0.85rem',
      }}>
        <div className="glass-card" style={{ padding: '1rem', borderRadius: 10 }}>
          <span className="section-label">Total Audit Logs</span>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem', lineHeight: 1 }}>
            {totalCount}
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>SHA-256 immutable records</span>
        </div>

        <div className="glass-card" style={{ padding: '1rem', borderRadius: 10 }}>
          <span className="section-label">Pending Review</span>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f59e0b', marginTop: '0.2rem', lineHeight: 1 }}>
            {pendingCount}
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>Awaiting Duty Officer action</span>
        </div>

        <div className="glass-card" style={{ padding: '1rem', borderRadius: 10 }}>
          <span className="section-label">Officer Confirmed</span>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#10b981', marginTop: '0.2rem', lineHeight: 1 }}>
            {confirmedCount}
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>Verified by Human-in-the-Loop</span>
        </div>

        <div className="glass-card" style={{ padding: '1rem', borderRadius: 10 }}>
          <span className="section-label">Escalated Threats</span>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f43f5e', marginTop: '0.2rem', lineHeight: 1 }}>
            {escalatedCount}
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>Sent to Cyber Cell & LEA</span>
        </div>
      </div>

      {/* ── Module Filter Bar ─────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <span className="section-label" style={{ margin: 0, marginRight: '0.4rem' }}>Filter Module:</span>
        {MODULES.map(m => (
          <button
            key={m}
            type="button"
            onClick={() => setSelectedModule(m)}
            className="btn-secondary"
            style={{
              padding: '0.25rem 0.65rem',
              fontSize: '0.75rem',
              borderRadius: 6,
              fontWeight: selectedModule === m ? 700 : 400,
              background: selectedModule === m ? 'var(--nav-active-bg)' : undefined,
              color: selectedModule === m ? 'var(--nav-active-text)' : undefined,
            }}
          >
            {m === 'all' ? 'All Modules' : m.replace(/_/g, ' ').toUpperCase()}
          </button>
        ))}
      </div>

      {/* ── Clean Humanized Data Table ───────────────────────────────── */}
      <div className="glass-card" style={{ borderRadius: 10, overflow: 'hidden', padding: 0 }}>
        {error && (
          <div style={{ padding: '1rem 1.25rem', color: '#f43f5e', fontSize: '0.875rem', background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-subtle)', fontWeight: 400 }}>
            Error loading audit log: {error}
          </div>
        )}

        {loading && events.length === 0 ? (
          <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {[1,2,3,4,5].map(i => <div key={i} className="skeleton" style={{ height: 36 }} />)}
          </div>
        ) : events.length === 0 ? (
          <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)', fontWeight: 400 }}>
            No audit records found for module "{selectedModule}". Run any analysis module (Scam, Counterfeit, Geospatial, Citizen Shield) to generate legal audit records.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 40, textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      title="Select all reviewed events"
                      checked={selectedForFIR.size > 0 && events.filter(e => e.review_action && e.review_action !== 'pending').every(e => selectedForFIR.has(e.event_id))}
                      onChange={e => {
                        const reviewedIds = events.filter(ev => ev.review_action && ev.review_action !== 'pending').map(ev => ev.event_id)
                        setSelectedForFIR(e.target.checked ? new Set(reviewedIds) : new Set())
                      }}
                      style={{ accentColor: '#3b82f6', cursor: 'pointer' }}
                    />
                  </th>
                  <th>Event ID & Hash</th>
                  <th>Timestamp</th>
                  <th>Module</th>
                  <th>AI Confidence</th>
                  <th>Officer Review Action</th>
                  <th>Sec 65B Export</th>
                </tr>
              </thead>
              <tbody>
                {events.map(ev => (
                  <Fragment key={ev.event_id}>
                    <tr onClick={() => void openDetail(ev.event_id)} style={{ cursor: 'pointer', background: selectedId === ev.event_id ? 'var(--bg-hover)' : undefined }}>
                      {/* FIR selection checkbox */}
                      <td style={{ textAlign: 'center', verticalAlign: 'middle' }} onClick={e => e.stopPropagation()}>
                        {(ev.review_action === 'confirm' || ev.review_action === 'confirmed' || ev.review_action === 'escalate' || ev.review_action === 'escalated') && (
                          <input
                            type="checkbox"
                            checked={selectedForFIR.has(ev.event_id)}
                            onChange={e => {
                              e.stopPropagation()
                              setSelectedForFIR(prev => {
                                const next = new Set(prev)
                                if (next.has(ev.event_id)) next.delete(ev.event_id)
                                else next.add(ev.event_id)
                                return next
                              })
                            }}
                            style={{ accentColor: '#3b82f6', cursor: 'pointer' }}
                            title="Select for FIR draft"
                          />
                        )}
                      </td>
                      <td>
                        <div style={{ fontFamily: 'monospace', fontSize: '0.8125rem', color: 'var(--text-primary)', fontWeight: 700 }}>
                          {ev.event_id.slice(0, 16)}...
                        </div>
                        {ev.input_hash && (
                          <div style={{ fontFamily: 'monospace', fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                            SHA: {ev.input_hash.slice(0, 12)}...
                          </div>
                        )}
                      </td>
                      <td style={{ whiteSpace: 'nowrap', fontWeight: 400, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {formatTimestamp(ev.timestamp)}
                      </td>
                      <td><ModuleBadge name={ev.module_name} /></td>
                      <td>
                        <ConfidencePill score={ev.confidence_score} />
                      </td>
                      <td>
                        <ReviewStatusCell action={ev.review_action ?? null} />
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={(e) => {
                            e.stopPropagation()
                            void openDossier(ev.event_id)
                          }}
                          style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', borderRadius: 6, fontWeight: 400 }}
                        >
                          Sec 65B Certificate
                        </button>
                      </td>
                    </tr>

                    {/* Detailed Drawer */}
                    {selectedId === ev.event_id && (
                      <tr key={`${ev.event_id}-detail`}>
                        <td colSpan={7} style={{ padding: '1.2rem', background: 'var(--bg-elevated)', borderTop: '1px solid var(--border-subtle)' }}>
                          {detailLoading ? (
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                              <span className="spinner" />
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 400 }}>Fetching tamper-evident audit record...</span>
                            </div>
                          ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                              
                              {/* Human Review Action Bar */}
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 1rem', background: 'var(--card-bg)', borderRadius: 10, border: '1px solid var(--border-default)', flexWrap: 'wrap', gap: '0.75rem' }}>
                                <div>
                                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block' }}>
                                    Human Officer Review Action
                                  </span>
                                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                                    Appends chained audit record to database preserving legal evidence integrity
                                  </span>
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                  <button
                                    disabled={reviewSubmitting}
                                    onClick={(e) => { e.stopPropagation(); void handleReview(ev.event_id, 'confirm') }}
                                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.4rem 0.85rem', borderRadius: 8, background: '#10b981', color: '#ffffff', fontWeight: 400, border: 'none', cursor: 'pointer', minHeight: 34, fontSize: '0.78rem' }}
                                  >
                                    Confirm Decision
                                  </button>
                                  <button
                                    disabled={reviewSubmitting}
                                    onClick={(e) => { e.stopPropagation(); void handleReview(ev.event_id, 'dismiss') }}
                                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.4rem 0.85rem', borderRadius: 8, background: 'var(--bg-elevated)', color: 'var(--text-primary)', fontWeight: 400, border: '1px solid var(--border-default)', cursor: 'pointer', minHeight: 34, fontSize: '0.78rem' }}
                                  >
                                    Dismiss False Alarm
                                  </button>
                                  <button
                                    disabled={reviewSubmitting}
                                    onClick={(e) => { e.stopPropagation(); void handleReview(ev.event_id, 'escalate') }}
                                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.4rem 0.85rem', borderRadius: 8, background: '#f43f5e', color: '#ffffff', fontWeight: 400, border: 'none', cursor: 'pointer', minHeight: 34, fontSize: '0.78rem' }}
                                  >
                                    Escalate to Cyber Cell
                                  </button>
                                </div>
                              </div>

                              {detail && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                    {detail.model_version && <span className="tag">Model: {detail.model_version}</span>}
                                    {detail.human_reviewer && <span className="tag">Reviewer: {detail.human_reviewer}</span>}
                                    {detail.prev_event_hash && <span className="tag">Prev Hash: {detail.prev_event_hash.slice(0, 16)}...</span>}
                                    {detail.event_hash && <span className="tag">Block Hash: {detail.event_hash.slice(0, 16)}...</span>}
                                  </div>
                                  <JsonViewer data={detail} title="Immutable Audit Record Payload" defaultOpen={true} />
                                </div>
                              )}

                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Section 65B Printable Dossier Modal ─────────────────────── */}
      {(dossierModal || dossierLoading) && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem'
        }}>
          <div style={{
            background: '#ffffff', color: '#000000', width: '100%', maxWidth: 750, maxHeight: '90vh',
            overflowY: 'auto', borderRadius: 12, padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.25rem'
          }}>
            {dossierLoading ? (
              <div style={{ padding: '2rem', textAlign: 'center' }}>Generating Section 65B Certificate...</div>
            ) : dossierModal ? (
              <>
                {/* Official Letterhead */}
                <div style={{ borderBottom: '2px solid #000', paddingBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800, textTransform: 'uppercase' }}>Government of India / Public Safety Division</h2>
                    <h3 style={{ margin: '0.2rem 0 0', fontSize: '0.85rem', fontWeight: 700, color: '#333' }}>DIGITAL EVIDENCE ADMISSIBILITY CERTIFICATE</h3>
                  </div>
                  <div style={{ textAlign: 'right', fontSize: '0.75rem', color: '#555' }}>
                    <div>Ref ID: {dossierModal.event_id.slice(0, 12)}</div>
                    <div>Date: {dossierModal.timestamp_ist}</div>
                  </div>
                </div>

                {/* Title */}
                <div style={{ textAlign: 'center', margin: '0.5rem 0' }}>
                  <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800 }}>{dossierModal.certificate_title}</h4>
                </div>

                {/* Statutory Clause */}
                <p style={{ fontSize: '0.82rem', lineHeight: 1.6, textAlign: 'justify', margin: 0 }}>
                  {dossierModal.statutory_certification_clause}
                </p>

                {/* Case Parameters Table */}
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', border: '1px solid #ccc' }}>
                  <tbody>
                    <tr>
                      <td style={{ padding: '0.4rem 0.6rem', fontWeight: 700, border: '1px solid #ccc', background: '#f5f5f5' }}>Module Name</td>
                      <td style={{ padding: '0.4rem 0.6rem', border: '1px solid #ccc' }}>{dossierModal.module_name}</td>
                    </tr>
                    <tr>
                      <td style={{ padding: '0.4rem 0.6rem', fontWeight: 700, border: '1px solid #ccc', background: '#f5f5f5' }}>AI Confidence Score</td>
                      <td style={{ padding: '0.4rem 0.6rem', border: '1px solid #ccc' }}>{Math.round(dossierModal.confidence_score * 100)}%</td>
                    </tr>
                    <tr>
                      <td style={{ padding: '0.4rem 0.6rem', fontWeight: 700, border: '1px solid #ccc', background: '#f5f5f5' }}>Cryptographic Input Hash</td>
                      <td style={{ padding: '0.4rem 0.6rem', border: '1px solid #ccc', fontFamily: 'monospace', fontSize: '0.75rem' }}>{dossierModal.input_hash}</td>
                    </tr>
                    <tr>
                      <td style={{ padding: '0.4rem 0.6rem', fontWeight: 700, border: '1px solid #ccc', background: '#f5f5f5' }}>Immutable Event Block Hash</td>
                      <td style={{ padding: '0.4rem 0.6rem', border: '1px solid #ccc', fontFamily: 'monospace', fontSize: '0.75rem' }}>{dossierModal.event_hash}</td>
                    </tr>
                  </tbody>
                </table>

                {/* Seal */}
                <div style={{ padding: '0.75rem', background: '#f9f9f9', border: '1px solid #ddd', fontSize: '0.72rem', fontFamily: 'monospace' }}>
                  {dossierModal.cryptographic_seal}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
                  <button type="button" onClick={() => window.print()} style={{ padding: '0.4rem 1rem', background: '#000', color: '#fff', border: 'none', borderRadius: 6, fontWeight: 700, cursor: 'pointer' }}>
                    Print / Save PDF
                  </button>
                  <button type="button" onClick={() => setDossierModal(null)} style={{ padding: '0.4rem 1rem', background: '#eee', color: '#000', border: '1px solid #ccc', borderRadius: 6, cursor: 'pointer' }}>
                    Close
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {events.length < totalCount && !loading && (
        <div style={{ textAlign: 'center' }}>
          <button className="btn-secondary" onClick={() => void loadEvents(page + 1)} style={{ borderRadius: 8, fontWeight: 400 }}>
            Load more audit records
          </button>
        </div>
      )}

      {/* FIR Draft Action Bar */}
      {selectedForFIR.size > 0 && (
        <div style={{
          position: 'sticky', bottom: 0,
          background: 'var(--card-bg)', border: '1px solid #3b82f6',
          borderRadius: 10, padding: '0.85rem 1.25rem',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem',
          boxShadow: '0 -4px 24px rgba(59,130,246,0.18)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#3b82f6', display: 'inline-block' }} />
            <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {selectedForFIR.size} event{selectedForFIR.size !== 1 ? 's' : ''} selected for FIR draft
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Only confirmed / escalated events can be used as evidence
            </span>
          </div>
          <div style={{ display: 'flex', gap: '0.65rem', alignItems: 'center' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setSelectedForFIR(new Set())}
              style={{ borderRadius: 8, fontSize: '0.8rem' }}
            >
              Clear Selection
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => setFirModalOpen(true)}
              style={{ borderRadius: 8, fontWeight: 700, background: '#3b82f6', fontSize: '0.88rem' }}
            >
              Draft Complaint
            </button>
          </div>
        </div>
      )}

      {/* FIR Draft Modal */}
      {firModalOpen && (
        <FIRDraftModal
          selectedEvents={events.filter(e => selectedForFIR.has(e.event_id))}
          onClose={() => setFirModalOpen(false)}
        />
      )}
    </div>
  )
}

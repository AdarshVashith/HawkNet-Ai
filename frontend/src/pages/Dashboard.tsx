import { type ReactNode, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getHealth, listAuditEvents, listFraudClusters, verifyAuditChain, reviewAuditEvent, type HealthResponse } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import StatusDot from '../components/StatusDot'

interface ModuleCard {
  id: string
  to: string
  name: string
  description: string
  risk: 'low' | 'medium' | 'high' | 'critical'
  moduleKey: string
  icon: ReactNode
}

type AuditEvent = {
  event_id: string
  timestamp: string
  module_name: string
  confidence_score: number
  review_action: string | null
  risk_level?: string
}


function IconShield() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  )
}
function IconTag() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
      <line x1="7" y1="7" x2="7.01" y2="7"/>
    </svg>
  )
}
function IconGraph() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
    </svg>
  )
}
function IconMap() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
      <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
    </svg>
  )
}
function IconUser() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
    </svg>
  )
}
function IconClipboard() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>
    </svg>
  )
}
function IconActivity() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  )
}
function IconTarget() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
    </svg>
  )
}
function IconLock() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  )
}

const MODULES: ModuleCard[] = [
  {
    id: 'scam',
    to: '/scam-detection',
    name: 'Scam Detection',
    description: 'NLP-powered analysis of SMS, email, voice, and social messages for phishing and digital arrest calls.',
    risk: 'high',
    moduleKey: 'scam_detection',
    icon: <IconShield />,
  },
  {
    id: 'counterfeit',
    to: '/counterfeit',
    name: 'Counterfeit Detector',
    description: 'Marketplace listing scoring to flag replica products, fake currency notes, and fake seller patterns.',
    risk: 'medium',
    moduleKey: 'counterfeit',
    icon: <IconTag />,
  },
  {
    id: 'fraud-graph',
    to: '/fraud-graph',
    name: 'Fraud Graph',
    description: 'Graph-based network analysis to detect coordinated fraud rings, shared devices, and suspicious entity clusters.',
    risk: 'critical',
    moduleKey: 'fraud_graph',
    icon: <IconGraph />,
  },
  {
    id: 'geospatial',
    to: '/geospatial',
    name: 'Geospatial Risk',
    description: 'Location-based crime hotspot mapping and real-time risk scoring for any lat/lng within configurable radius.',
    risk: 'medium',
    moduleKey: 'geospatial',
    icon: <IconMap />,
  },
  {
    id: 'citizen-shield',
    to: '/citizen-shield',
    name: 'Citizen Shield',
    description: 'Anonymous citizen report intake for scams, counterfeit goods, harassment incidents, and public threats.',
    risk: 'low',
    moduleKey: 'citizen_shield',
    icon: <IconUser />,
  },
  {
    id: 'audit',
    to: '/audit',
    name: 'Audit Log',
    description: 'Tamper-evident hash-chained audit trail for all AI model decisions with chain integrity verification.',
    risk: 'low',
    moduleKey: 'audit',
    icon: <IconClipboard />,
  },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthStatus, setHealthStatus] = useState<'ok' | 'error' | 'loading'>('loading')

  const [allEvents, setAllEvents] = useState<AuditEvent[]>([])
  const [totalEvents, setTotalEvents] = useState(0)
  const [clustersCount, setClustersCount] = useState(0)
  const [chainVerifiedCount, setChainVerifiedCount] = useState(0)
  const [chainValid, setChainValid] = useState(true)
  const [loadingData, setLoadingData] = useState(true)
  const [reviewBusy, setReviewBusy] = useState(false)

  useEffect(() => {
    loadDashboardData()
  }, [])

  async function loadDashboardData() {
    setLoadingData(true)
    try {
      const [healthRes, auditRes, clustersRes, chainRes] = await Promise.all([
        getHealth().catch(() => null),
        listAuditEvents(0, 200).catch(() => ({ events: [], total: 0 })),
        listFraudClusters().catch(() => []),
        verifyAuditChain().catch(() => ({ checked_count: 0, valid: true, message: '' })),
      ])

      if (healthRes) {
        setHealth(healthRes)
        setHealthStatus('ok')
      } else {
        setHealthStatus('error')
      }

      const resObj = auditRes as unknown as { events?: AuditEvent[]; total?: number }
      const eventsArr = Array.isArray(resObj?.events) ? resObj.events : (Array.isArray(auditRes) ? (auditRes as AuditEvent[]) : [])
      setAllEvents(eventsArr)
      setTotalEvents(resObj?.total ?? eventsArr.length)

      const clusterArr = Array.isArray(clustersRes) ? clustersRes : []
      setClustersCount(clusterArr.length)

      setChainVerifiedCount(chainRes.checked_count)
      setChainValid(chainRes.valid)
    } finally {
      setLoadingData(false)
    }
  }

  async function handleQuickReview(eventId: string, action: 'confirm' | 'dismiss' | 'escalate') {
    setReviewBusy(true)
    try {
      await reviewAuditEvent(eventId, action, 'Duty Officer')
      await loadDashboardData()
    } catch {
      // ignore
    } finally {
      setReviewBusy(false)
    }
  }

  // Real Calculated Metrics from API Audit Trail
  const reviewedCount = allEvents.filter(e => e.review_action !== null).length
  const pendingCount = Math.max(0, allEvents.length - reviewedCount)

  const avgConfidence = allEvents.length > 0
    ? Math.round((allEvents.reduce((acc, curr) => acc + (curr.confidence_score || 0), 0) / allEvents.length) * 100)
    : 0

  const highRiskCount = allEvents.filter(e => e.risk_level === 'high' || e.risk_level === 'critical').length
  const mediumRiskCount = allEvents.filter(e => e.risk_level === 'medium').length
  const lowRiskCount = allEvents.filter(e => e.risk_level === 'low' || !e.risk_level).length

  // Real per-module event counts from database
  const getModuleEventCount = (key: string) => {
    return allEvents.filter(e => e.module_name?.toLowerCase().includes(key) || (key === 'audit' && e.module_name === 'human_review')).length
  }

  return (
    <div className="animate-fade-in" style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* ── Real Telemetry Metrics (4 Cards) ────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '1.0rem',
      }}>
        {/* KPI 1: Real Total Audit Events */}
        <div className="glass-card" style={{ padding: '1.1rem 1.25rem', borderRadius: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>Total AI Decisions Logged</span>
            <div style={{ color: 'var(--text-muted)' }}><IconActivity /></div>
          </div>
          <div style={{ fontSize: '1.7rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em', lineHeight: 1 }}>
            {loadingData ? <span className="spinner" /> : totalEvents}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: 400 }}>
            {reviewedCount} reviewed · {pendingCount} pending officer decision
          </div>
        </div>

        {/* KPI 2: Real Active Fraud Clusters */}
        <div className="glass-card" style={{ padding: '1.1rem 1.25rem', borderRadius: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>Active Fraud Clusters</span>
            <span style={{ fontSize: '0.72rem', color: clustersCount > 0 ? '#f59e0b' : '#10b981', fontWeight: 400 }}>
              {clustersCount > 0 ? 'Detected' : 'Clear'}
            </span>
          </div>
          <div style={{ fontSize: '1.7rem', fontWeight: 700, color: clustersCount > 0 ? '#f59e0b' : 'var(--text-primary)', letterSpacing: '-0.02em', lineHeight: 1 }}>
            {loadingData ? <span className="spinner" /> : clustersCount}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: 400 }}>
            Real-time entity network graph clusters
          </div>
        </div>

        {/* KPI 3: Real Average Confidence */}
        <div className="glass-card" style={{ padding: '1.1rem 1.25rem', borderRadius: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>Avg AI Model Confidence</span>
            <IconTarget />
          </div>
          <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#10b981', letterSpacing: '-0.02em', lineHeight: 1 }}>
            {loadingData ? <span className="spinner" /> : `${avgConfidence}%`}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: 400 }}>
            Mean confidence across all evaluated inputs
          </div>
        </div>

        {/* KPI 4: Real SHA-256 Hash Chain Status */}
        <div className="glass-card" style={{ padding: '1.1rem 1.25rem', borderRadius: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>Hash Chain Verification</span>
            <IconLock />
          </div>
          <div style={{ fontSize: '1.7rem', fontWeight: 700, color: chainValid ? '#10b981' : '#f43f5e', letterSpacing: '-0.02em', lineHeight: 1 }}>
            {loadingData ? <span className="spinner" /> : (chainValid ? 'Valid' : 'Tampered')}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: 400 }}>
            {chainVerifiedCount} consecutive entries verified via SHA-256
          </div>
        </div>
      </div>

      {/* ── Pro UI 2-Column Split: Real Audit Feed + Real Risk Breakdown ──── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
        gap: '1.0rem',
      }}>

        {/* Left Column: Real Live Audit Stream (Latest 5 events) */}
        <div className="glass-card" style={{ borderRadius: 10, overflow: 'hidden', padding: 0 }}>
          <div style={{ padding: '0.85rem 1.15rem', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Live Decision Stream & Human Review
              </h3>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                Real events fetched directly from backend audit trail
              </span>
            </div>
            <button className="btn-secondary" onClick={() => void navigate('/audit')} style={{ fontSize: '0.72rem', borderRadius: 8, padding: '0.25rem 0.65rem', fontWeight: 400 }}>
              View All &rarr;
            </button>
          </div>

          {allEvents.length === 0 ? (
            <div style={{ padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.8125rem', fontWeight: 400 }}>
              {loadingData ? 'Fetching audit records...' : 'No decision records found.'}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {allEvents.slice(0, 5).map((ev) => {
                const displayModule =
                  ev.module_name === 'scam_detection' ? 'Scam Detection'
                  : ev.module_name === 'counterfeit' ? 'Counterfeit Detector'
                  : ev.module_name === 'fraud_graph' ? 'Fraud Graph'
                  : ev.module_name === 'geospatial' ? 'Geospatial Risk'
                  : ev.module_name === 'citizen_shield' ? 'Citizen Shield'
                  : ev.module_name === 'human_review' ? 'Human Officer Review'
                  : ev.module_name

                return (
                  <div key={ev.event_id} style={{
                    padding: '0.75rem 1.15rem',
                    borderBottom: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '0.75rem',
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.15rem' }}>
                        <span className="tag">{displayModule}</span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                          {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-primary)', fontWeight: 400 }}>
                        ID: {ev.event_id.slice(0, 16)}...
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 400, color: ev.confidence_score >= 0.7 ? '#10b981' : ev.confidence_score >= 0.4 ? '#f59e0b' : '#f43f5e' }}>
                        {Math.round(ev.confidence_score * 100)}%
                      </span>
                      {ev.risk_level && <RiskBadge level={ev.risk_level} />}

                      {!ev.review_action ? (
                        <button
                          disabled={reviewBusy}
                          onClick={() => void handleQuickReview(ev.event_id, 'confirm')}
                          className="btn-secondary"
                          style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', borderRadius: 6, fontWeight: 400 }}
                        >
                          Confirm
                        </button>
                      ) : (
                        <span className="tag" style={{ fontSize: '0.68rem' }}>{ev.review_action.toUpperCase()}</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Column: Real Risk Level Distribution */}
        <div className="glass-card" style={{ padding: '1.15rem', borderRadius: 10 }}>
          <div style={{ marginBottom: '0.85rem' }}>
            <h3 style={{ margin: 0, fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Real Risk Tier Breakdown
            </h3>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
              Calculated live across {allEvents.length} decision records
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.3rem' }}>
                <span style={{ color: '#f43f5e', fontWeight: 400 }}>High / Critical Risk ({allEvents.length > 0 ? Math.round((highRiskCount / allEvents.length) * 100) : 0}%)</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 400 }}>{highRiskCount} incidents</span>
              </div>
              <div style={{ height: 6, width: '100%', background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ width: `${allEvents.length > 0 ? (highRiskCount / allEvents.length) * 100 : 0}%`, height: '100%', background: '#f43f5e', transition: 'width 0.4s ease' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.3rem' }}>
                <span style={{ color: '#f59e0b', fontWeight: 400 }}>Medium Risk ({allEvents.length > 0 ? Math.round((mediumRiskCount / allEvents.length) * 100) : 0}%)</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 400 }}>{mediumRiskCount} incidents</span>
              </div>
              <div style={{ height: 6, width: '100%', background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ width: `${allEvents.length > 0 ? (mediumRiskCount / allEvents.length) * 100 : 0}%`, height: '100%', background: '#f59e0b', transition: 'width 0.4s ease' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.3rem' }}>
                <span style={{ color: '#10b981', fontWeight: 400 }}>Low / Safe ({allEvents.length > 0 ? Math.round((lowRiskCount / allEvents.length) * 100) : 0}%)</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 400 }}>{lowRiskCount} incidents</span>
              </div>
              <div style={{ height: 6, width: '100%', background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ width: `${allEvents.length > 0 ? (lowRiskCount / allEvents.length) * 100 : 0}%`, height: '100%', background: '#10b981', transition: 'width 0.4s ease' }} />
              </div>
            </div>

            <div style={{ marginTop: '0.5rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem' }}>
              <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>Active Database Records: {totalEvents}</span>
              <span style={{ color: 'var(--text-muted)', fontWeight: 400, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <StatusDot status={healthStatus} />
                {healthStatus === 'ok' ? `${health?.service} Operational` : 'Connecting...'}
              </span>
            </div>
          </div>
        </div>

      </div>

      {/* ── AI Modules Quick Launcher (6 Clean Cards with Real Counts) ──────── */}
      <div>
        <p className="section-label" style={{ marginBottom: '0.6rem' }}>AI Safety Modules</p>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(310px, 1fr))',
          gap: '1rem',
        }}>
          {MODULES.map((mod) => {
            const count = getModuleEventCount(mod.moduleKey)

            return (
              <button
                key={mod.id}
                onClick={() => void navigate(mod.to)}
                style={{
                  all: 'unset',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  padding: '1.25rem',
                  background: 'var(--card-bg)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 10,
                  textAlign: 'left',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.2s ease, transform 0.2s ease',
                  boxShadow: 'var(--shadow-card)',
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-strong)' }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-subtle)' }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <div style={{
                    padding: '0.5rem',
                    background: 'var(--bg-elevated)',
                    borderRadius: 8,
                    color: 'var(--text-primary)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {mod.icon}
                  </div>
                  <RiskBadge level={mod.risk} />
                </div>

                <h3 style={{ margin: '0 0 0.35rem', fontSize: '1.02rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                  {mod.name}
                </h3>
                <p style={{ margin: '0 0 0.85rem', fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.5, flex: 1, fontWeight: 400 }}>
                  {mod.description}
                </p>

                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  paddingTop: '0.75rem',
                  borderTop: '1px solid var(--border-subtle)',
                }}>
                  <div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>{count}</div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 400 }}>Evaluated events</div>
                  </div>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round">
                    <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                  </svg>
                </div>
              </button>
            )
          })}
        </div>
      </div>

    </div>
  )
}

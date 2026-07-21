import { useEffect, useState, type FormEvent } from 'react'
import {
  analyzeFraudGraph,
  listFraudClusters,
  exportFraudClusterPackage,
  type GraphEntity,
  type GraphEdge,
  type SuspiciousCluster,
} from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import JsonViewer from '../components/JsonViewer'

type AnalysisResult = {
  request_id: string
  risk_level: string
  risk_score: number
  cluster_size: number
  suspicious_entities: string[]
  explanation: string
  model_version: string
  community_id?: string
}

type IntelPackage = {
  package_type: string
  cluster_id: string
  generated_at: string
  confidence: number
  suspicion_score: number
  summary: string
  member_accounts: string[]
  member_phones: string[]
  member_devices: string[]
  evidence_trail: string[]
  recommended_actions: string[]
  audit_log_reference: string
}

const PRESET_GRAPH_NETWORKS = [
  {
    name: 'Syndicate Mule Ring A-7',
    tag: 'MULE RING',
    color: '#f43f5e',
    seed: 'acct-101',
    entities: [
      { id: 'acct-101', type: 'account' },
      { id: 'acct-102', type: 'account' },
      { id: 'acct-103', type: 'account' },
      { id: 'device-88', type: 'device' },
      { id: 'phone-99', type: 'phone' },
    ],
    edges: [
      { source: 'acct-101', target: 'device-88', relation: 'uses_device' },
      { source: 'acct-102', target: 'device-88', relation: 'uses_device' },
      { source: 'acct-103', target: 'device-88', relation: 'uses_device' },
      { source: 'acct-101', target: 'phone-99', relation: 'linked_phone' },
    ],
  },
  {
    name: 'Crypto Laundering Hub B-12',
    tag: 'RAPID STRUCTURING',
    color: '#f97316',
    seed: 'acct-201',
    entities: [
      { id: 'acct-201', type: 'account' },
      { id: 'acct-202', type: 'account' },
      { id: 'merchant-77', type: 'merchant' },
      { id: 'device-55', type: 'device' },
    ],
    edges: [
      { source: 'acct-201', target: 'acct-202', relation: 'fund_transfer' },
      { source: 'acct-202', target: 'merchant-77', relation: 'crypto_purchase' },
      { source: 'acct-201', target: 'device-55', relation: 'login_device' },
    ],
  },
  {
    name: 'Call Center Extortion Network',
    tag: 'IMEI CLUSTER',
    color: '#f59e0b',
    seed: 'phone-555',
    entities: [
      { id: 'phone-555', type: 'phone' },
      { id: 'acct-301', type: 'account' },
      { id: 'acct-302', type: 'account' },
    ],
    edges: [
      { source: 'phone-555', target: 'acct-301', relation: 'registered_to' },
      { source: 'phone-555', target: 'acct-302', relation: 'registered_to' },
    ],
  },
]

function RiskGauge({ score }: { score: number }) {
  const pct = Math.min(Math.max(score, 0), 1)
  const color = pct < 0.35 ? '#10b981' : pct < 0.65 ? '#f59e0b' : pct < 0.85 ? '#f97316' : '#f43f5e'
  const r = 44
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem' }}>
      <div style={{ position: 'relative', width: 110, height: 110 }}>
        <svg width="110" height="110" viewBox="0 0 110 110" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="55" cy="55" r={r} fill="none" stroke="var(--border-default)" strokeWidth="8"/>
          <circle
            cx="55" cy="55" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
            strokeDasharray={circ} strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.6s ease' }}
          />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: '1.4rem', fontWeight: 700, color, lineHeight: 1 }}>{Math.round(pct * 100)}%</span>
          <span style={{ fontSize: '0.58rem', color: 'var(--text-muted)', fontWeight: 400, textTransform: 'uppercase', letterSpacing: '0.05em' }}>ring score</span>
        </div>
      </div>
      <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 400 }}>Mule Ring Density</span>
    </div>
  )
}

function IconNetwork() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
    </svg>
  )
}

function getNodeIconSymbol(type: string) {
  if (type === 'phone') return '📱'
  if (type === 'device') return '💻'
  if (type === 'merchant') return '🏪'
  return '👤'
}

export default function FraudGraph() {
  const [entities, setEntities] = useState<GraphEntity[]>(PRESET_GRAPH_NETWORKS[0].entities)
  const [edges, setEdges] = useState<GraphEdge[]>(PRESET_GRAPH_NETWORKS[0].edges)
  const [seedId, setSeedId] = useState('acct-101')
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)

  const [showNodeEditor, setShowNodeEditor] = useState(false)
  const [showEdgeEditor, setShowEdgeEditor] = useState(false)

  const [newEntityId, setNewEntityId] = useState('')
  const [newEntityType, setNewEntityType] = useState('account')

  const [newEdgeSource, setNewEdgeSource] = useState('')
  const [newEdgeTarget, setNewEdgeTarget] = useState('')
  const [newEdgeRelation, setNewEdgeRelation] = useState('linked')

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)

  const [clusters, setClusters] = useState<SuspiciousCluster[]>([])
  const [loadingClusters, setLoadingClusters] = useState(true)

  const [intelPackage, setIntelPackage] = useState<IntelPackage | null>(null)
  const [exportingId, setExportingId] = useState<string | null>(null)

  useEffect(() => {
    listFraudClusters()
      .then(res => {
        if (res?.clusters) setClusters(res.clusters)
      })
      .catch(() => {})
      .finally(() => setLoadingClusters(false))
  }, [])

  function handlePresetSelect(p: typeof PRESET_GRAPH_NETWORKS[0]) {
    setEntities(p.entities)
    setEdges(p.edges)
    setSeedId(p.seed)
    setResult(null)
    setIntelPackage(null)
    setError(null)
  }

  function handleClusterLoad(c: SuspiciousCluster) {
    const newEnts: GraphEntity[] = [
      ...c.member_accounts.map(a => ({ id: a, type: 'account' })),
      ...(c.member_phones || []).map(p => ({ id: p, type: 'phone' })),
      ...(c.member_devices || []).map(d => ({ id: d, type: 'device' })),
    ]

    const newEdg: GraphEdge[] = []
    const seed = c.member_accounts[0] || newEnts[0]?.id || 'seed'

    for (let i = 1; i < newEnts.length; i++) {
      newEdg.push({
        source: seed,
        target: newEnts[i].id,
        relation: newEnts[i].type === 'device' ? 'uses_device' : newEnts[i].type === 'phone' ? 'linked_phone' : 'fund_transfer'
      })
    }

    setEntities(newEnts)
    setEdges(newEdg)
    setSeedId(seed)
    setResult(null)
    setIntelPackage(null)
    setError(null)
  }

  function addEntity() {
    if (!newEntityId.trim()) return
    if (entities.some(e => e.id === newEntityId.trim())) return
    setEntities([...entities, { id: newEntityId.trim(), type: newEntityType }])
    setNewEntityId('')
  }

  function removeEntity(id: string) {
    setEntities(entities.filter(e => e.id !== id))
    setEdges(edges.filter(ed => ed.source !== id && ed.target !== id))
    if (seedId === id && entities.length > 1) {
      setSeedId(entities.find(e => e.id !== id)?.id || '')
    }
  }

  function addEdge() {
    if (!newEdgeSource || !newEdgeTarget || newEdgeSource === newEdgeTarget) return
    setEdges([...edges, { source: newEdgeSource, target: newEdgeTarget, relation: newEdgeRelation }])
    setNewEdgeSource('')
    setNewEdgeTarget('')
  }

  function removeEdge(idx: number) {
    setEdges(edges.filter((_, i) => i !== idx))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null); setResult(null); setIntelPackage(null)
    try {
      const data = await analyzeFraudGraph(entities, edges, seedId)
      setResult(data as AnalysisResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setBusy(false)
    }
  }

  async function handleExportPackage(clusterId: string) {
    setExportingId(clusterId)
    try {
      const pkg = await exportFraudClusterPackage(clusterId)
      setIntelPackage(pkg)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to export intelligence package')
    } finally {
      setExportingId(null)
    }
  }

  // Star-hub layout: Seed node in center (250, 160), neighbors placed gracefully around it
  const neighbors = entities.filter(e => e.id !== seedId)
  const seedNode = entities.find(e => e.id === seedId) || entities[0]

  return (
    <div className="animate-fade-in" style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* Page Header */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              Fraud Network & Mule Ring Graph Intelligence Studio
            </h2>
            <RiskBadge level="high" label="Community Detection" />
          </div>
          <p style={{ margin: '0.2rem 0 0', color: 'var(--text-secondary)', fontSize: '0.8125rem', fontWeight: 400 }}>
            Map multi-account device sharing, rapid pass-through structuring, and export official Law Enforcement Intelligence Packages.
          </p>
        </div>

        {/* Featured Network Presets */}
        <div>
          <p className="section-label" style={{ marginBottom: '0.45rem' }}>Featured Fraud Ring Topologies (Click to Load)</p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '0.75rem',
          }}>
            {PRESET_GRAPH_NETWORKS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                className="glass-card"
                onClick={() => handlePresetSelect(p)}
                style={{
                  padding: '0.85rem 1rem',
                  borderRadius: 10,
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.35rem',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--card-bg)',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-primary)' }}>
                    <IconNetwork />
                    <span style={{ fontSize: '0.82rem', fontWeight: 700 }}>{p.name}</span>
                  </div>
                  <span style={{
                    fontSize: '0.62rem', fontWeight: 700, color: p.color,
                    padding: '0.1rem 0.4rem', background: 'var(--bg-elevated)',
                    borderRadius: 6, border: `1px solid ${p.color}`
                  }}>
                    {p.tag}
                  </span>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 400 }}>
                  {p.entities.length} Nodes · {p.edges.length} Links (Seed: {p.seed})
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── 2-Column Studio Layout ────────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))',
        gap: '1.25rem',
        alignItems: 'flex-start',
      }}>
        
        {/* Left Column: Visual Canvas & Entity Editor */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {/* Organic Star Graph Diagram SVG */}
          <div className="glass-card" style={{ padding: '1rem', borderRadius: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <div>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <IconNetwork /> Star-Hub Network Visualizer
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                  Seed Entity centered. Click surrounding node to refocus topology.
                </span>
              </div>
              <span className="tag" style={{ fontSize: '0.7rem' }}>{entities.length} Nodes / {edges.length} Links</span>
            </div>

            <div style={{
              width: '100%',
              height: 320,
              background: 'var(--bg-elevated)',
              borderRadius: 8,
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid var(--border-subtle)',
              overflow: 'hidden',
            }}>
              <svg width="100%" height="100%" viewBox="0 0 500 320">
                {/* 1. Center Seed Node (250, 160) */}
                {seedNode && (() => {
                  const isSuspicious = result?.suspicious_entities?.includes(seedNode.id)

                  return (
                    <g key={seedNode.id} onMouseEnter={() => setHoveredNode(seedNode.id)} onMouseLeave={() => setHoveredNode(null)}>
                      <circle cx="250" cy="160" r="28" fill="var(--card-bg)" stroke={isSuspicious ? '#f43f5e' : '#f59e0b'} strokeWidth="3.5" />
                      <text x="250" y="156" fill="var(--text-primary)" fontSize="14" textAnchor="middle">{getNodeIconSymbol(seedNode.type)}</text>
                      <text x="250" y="172" fill="var(--text-primary)" fontSize="9" textAnchor="middle" fontWeight="bold">{seedNode.id.slice(0, 10)}</text>
                      <text x="250" y="198" fill="#f59e0b" fontSize="8" textAnchor="middle" fontWeight="bold">★ PRIMARY SEED</text>
                    </g>
                  )
                })()}

                {/* 2. Surrounding Neighbor Nodes */}
                {neighbors.map((ent, idx) => {
                  const total = Math.max(neighbors.length, 1)
                  const radius = 120
                  const angle = (2 * Math.PI * idx) / total - Math.PI / 2
                  const cx = 250 + radius * Math.cos(angle)
                  const cy = 160 + radius * Math.sin(angle)

                  const edge = edges.find(ed => (ed.source === seedNode?.id && ed.target === ent.id) || (ed.target === seedNode?.id && ed.source === ent.id))
                  const isHovered = hoveredNode === ent.id || hoveredNode === seedNode?.id
                  const isSuspicious = result?.suspicious_entities?.includes(ent.id)
                  const nodeColor = isSuspicious ? '#f43f5e' : ent.type === 'device' ? '#3b82f6' : ent.type === 'phone' ? '#a855f7' : '#10b981'

                  return (
                    <g key={ent.id} onClick={() => setSeedId(ent.id)} onMouseEnter={() => setHoveredNode(ent.id)} onMouseLeave={() => setHoveredNode(null)} style={{ cursor: 'pointer' }}>
                      {/* Connection Line */}
                      <line
                        x1="250" y1="160" x2={cx} y2={cy}
                        stroke={isHovered ? '#10b981' : 'var(--border-strong)'}
                        strokeWidth={isHovered ? '2.5' : '1.5'}
                        strokeDasharray={isHovered ? undefined : '3 3'}
                      />

                      {/* Edge Relation Hover Label */}
                      {isHovered && edge && (
                        <rect x={(250 + cx) / 2 - 28} y={(160 + cy) / 2 - 8} width="56" height="14" rx="4" fill="var(--card-bg)" stroke="#10b981" />
                      )}
                      {isHovered && edge && (
                        <text x={(250 + cx) / 2} y={(160 + cy) / 2 + 2} fill="#10b981" fontSize="8" textAnchor="middle" fontWeight="bold">{edge.relation}</text>
                      )}

                      {/* Node Circle */}
                      <circle cx={cx} cy={cy} r="20" fill="var(--card-bg)" stroke={nodeColor} strokeWidth="2" />
                      <text x={cx} y={cy - 2} fill="var(--text-primary)" fontSize="12" textAnchor="middle">{getNodeIconSymbol(ent.type)}</text>
                      <text x={cx} y={cy + 11} fill="var(--text-primary)" fontSize="8" textAnchor="middle" fontWeight="bold">{ent.id.slice(0, 9)}</text>
                      <text x={cx} y={cy + 32} fill="var(--text-muted)" fontSize="7" textAnchor="middle">{ent.type.toUpperCase()}</text>
                    </g>
                  )
                })}
              </svg>
            </div>
          </div>

          {/* Clean Humanized Node & Link Controls */}
          <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              
              <div>
                <label className="section-label" htmlFor="fg-seed">Seed Entity for Cluster Analysis</label>
                <select id="fg-seed" className="input-field" value={seedId} onChange={e => setSeedId(e.target.value)} style={{ borderRadius: 8, fontWeight: 400 }}>
                  {entities.map(e => <option key={e.id} value={e.id}>{e.id} ({e.type})</option>)}
                </select>
              </div>

              {/* Collapsible Entity List */}
              <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '0.75rem', background: 'var(--bg-elevated)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Configured Network Nodes ({entities.length})
                  </span>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowNodeEditor(v => !v)}
                    style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', borderRadius: 6, fontWeight: 400 }}
                  >
                    {showNodeEditor ? 'Collapse' : 'Manage Nodes'}
                  </button>
                </div>

                {showNodeEditor && (
                  <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                      <input
                        className="input-field"
                        placeholder="Add ID (e.g. acct-9)"
                        value={newEntityId}
                        onChange={e => setNewEntityId(e.target.value)}
                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.78rem', borderRadius: 6 }}
                      />
                      <select
                        className="input-field"
                        value={newEntityType}
                        onChange={e => setNewEntityType(e.target.value)}
                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.78rem', width: 110, borderRadius: 6 }}
                      >
                        <option value="account">Account</option>
                        <option value="device">Device</option>
                        <option value="phone">Phone</option>
                        <option value="merchant">Merchant</option>
                      </select>
                      <button type="button" className="btn-secondary" onClick={addEntity} style={{ padding: '0.3rem 0.75rem', fontSize: '0.78rem', borderRadius: 6 }}>
                        + Add Node
                      </button>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', maxHeight: 150, overflowY: 'auto' }}>
                      {entities.map(e => (
                        <span key={e.id} className="tag" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                          {getNodeIconSymbol(e.type)} {e.id}
                          <button type="button" onClick={() => removeEntity(e.id)} style={{ background: 'none', border: 'none', color: '#f43f5e', cursor: 'pointer', padding: 0, marginLeft: 2 }}>×</button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Collapsible Edge List */}
              <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '0.75rem', background: 'var(--bg-elevated)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Relationship Links ({edges.length})
                  </span>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowEdgeEditor(v => !v)}
                    style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', borderRadius: 6, fontWeight: 400 }}
                  >
                    {showEdgeEditor ? 'Collapse' : 'Manage Links'}
                  </button>
                </div>

                {showEdgeEditor && (
                  <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                    <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                      <select className="input-field" value={newEdgeSource} onChange={e => setNewEdgeSource(e.target.value)} style={{ padding: '0.3rem 0.5rem', fontSize: '0.78rem', flex: 1, borderRadius: 6 }}>
                        <option value="">Source Node</option>
                        {entities.map(e => <option key={e.id} value={e.id}>{e.id}</option>)}
                      </select>
                      <select className="input-field" value={newEdgeRelation} onChange={e => setNewEdgeRelation(e.target.value)} style={{ padding: '0.3rem 0.5rem', fontSize: '0.78rem', flex: 1, borderRadius: 6 }}>
                        <option value="linked">linked</option>
                        <option value="uses_device">uses_device</option>
                        <option value="fund_transfer">fund_transfer</option>
                        <option value="registered_to">registered_to</option>
                      </select>
                      <select className="input-field" value={newEdgeTarget} onChange={e => setNewEdgeTarget(e.target.value)} style={{ padding: '0.3rem 0.5rem', fontSize: '0.78rem', flex: 1, borderRadius: 6 }}>
                        <option value="">Target Node</option>
                        {entities.map(e => <option key={e.id} value={e.id}>{e.id}</option>)}
                      </select>
                      <button type="button" className="btn-secondary" onClick={addEdge} style={{ padding: '0.3rem 0.75rem', fontSize: '0.78rem', borderRadius: 6 }}>
                        + Add Link
                      </button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', maxHeight: 150, overflowY: 'auto' }}>
                      {edges.map((ed, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.35rem 0.65rem', background: 'var(--card-bg)', borderRadius: 6, fontSize: '0.78rem' }}>
                          <span>{ed.source} ➔ {ed.target} ({ed.relation})</span>
                          <button type="button" onClick={() => removeEdge(i)} style={{ background: 'none', border: 'none', color: '#f43f5e', cursor: 'pointer' }}>×</button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <button className="btn-primary" disabled={busy} style={{ borderRadius: 8, fontWeight: 400, minHeight: 38 }}>
                {busy ? <span className="spinner" /> : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                )}
                {busy ? 'Running Community Detection...' : `Analyze Network Topology`}
              </button>
            </form>

            {error && (
              <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: 'var(--bg-elevated)', border: '1px solid #f43f5e', borderRadius: 8, color: '#f43f5e', fontSize: '0.85rem', fontWeight: 400 }}>
                Error: {error}
              </div>
            )}
          </div>

        </div>

        {/* Right Column: Intelligence Output & Enterprise Communities Table */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {result ? (
            <div className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                  <RiskGauge score={result.risk_score} />
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.6rem' }}>
                      <RiskBadge level={result.risk_level} />
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>Cluster Size: {result.cluster_size} Nodes</span>
                    </div>
                    <p style={{ margin: '0 0 0.85rem', fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, fontWeight: 400 }}>{result.explanation}</p>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontWeight: 400 }}>
                      Suspicious Entities Flagged: {result.suspicious_entities.join(', ') || 'None'}
                    </div>
                  </div>
                </div>
              </div>

              <JsonViewer data={result} title="Payload & Technical Config" defaultOpen={false} />
            </div>
          ) : (
            <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Discovered Mule Ring Communities
                  </h3>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    Official Community Detection Rankings & LEA Export
                  </span>
                </div>
                <span className="tag" style={{ fontSize: '0.7rem' }}>Live Database</span>
              </div>

              {loadingClusters ? (
                <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: 32 }} />)}
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Cluster ID</th>
                        <th>Members</th>
                        <th>Suspicion Score</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {clusters.map(c => (
                        <tr key={c.cluster_id} onClick={() => handleClusterLoad(c)} style={{ cursor: 'pointer' }}>
                          <td style={{ fontWeight: 700, fontFamily: 'monospace' }}>
                            #{c.rank} {c.cluster_id}
                          </td>
                          <td>
                            {c.size || c.member_accounts.length} members
                          </td>
                          <td>
                            <span style={{ fontWeight: 700, color: c.suspicion_score > 0.7 ? '#f43f5e' : c.suspicion_score > 0.3 ? '#f59e0b' : '#10b981' }}>
                              {Math.round(c.suspicion_score * 100)}%
                            </span>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="btn-secondary"
                              disabled={exportingId === c.cluster_id}
                              onClick={(e) => {
                                e.stopPropagation()
                                void handleExportPackage(c.cluster_id)
                              }}
                              style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', borderRadius: 6, fontWeight: 400 }}
                            >
                              {exportingId === c.cluster_id ? 'Exporting...' : '📄 Dossier'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Display Exported Dossier if clicked */}
              {intelPackage && (
                <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg-elevated)', border: '1px solid #10b981', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#10b981' }}>Law Enforcement Intelligence Dossier</span>
                    <span className="tag">Section 65B Audit Ref: {intelPackage.audit_log_reference.slice(0, 8)}...</span>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 400 }}>{intelPackage.summary}</p>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontWeight: 400 }}>
                    Recommended LEA Actions: {intelPackage.recommended_actions.join(' · ')}
                  </div>
                </div>
              )}
            </div>
          )}

        </div>

      </div>

    </div>
  )
}

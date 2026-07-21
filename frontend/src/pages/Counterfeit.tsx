import { useState, type FormEvent, type ChangeEvent } from 'react'
import { analyzeCounterfeit, scanCurrencyNote, type CurrencyScanResponse } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import JsonViewer from '../components/JsonViewer'

type CounterfeitResult = {
  request_id: string
  risk_level: string
  risk_score: number
  authenticity_score: number
  explanation: string
  model_version: string
  red_flags: string[]
}

function AuthenticityGauge({ score }: { score: number }) {
  const pct = Math.min(Math.max(score, 0), 1)
  const color =
    pct > 0.75 ? '#10b981'
    : pct > 0.50 ? '#f59e0b'
    : pct > 0.25 ? '#f97316'
    : '#f43f5e'
  const r = 42
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem' }}>
      <div style={{ position: 'relative', width: 110, height: 110 }}>
        <svg width="110" height="110" viewBox="0 0 110 110" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="55" cy="55" r={r} fill="none" stroke="var(--border-default)" strokeWidth="8"/>
          <circle
            cx="55" cy="55" r={r} fill="none"
            stroke={color} strokeWidth="8" strokeLinecap="round"
            strokeDasharray={circ} strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.6s ease' }}
          />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: '1.35rem', fontWeight: 700, color, lineHeight: 1 }}>{Math.round(pct * 100)}%</span>
          <span style={{ fontSize: '0.58rem', color: 'var(--text-muted)', fontWeight: 400, textTransform: 'uppercase', letterSpacing: '0.05em' }}>auth score</span>
        </div>
      </div>
      <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 400 }}>Authenticity Rating</span>
    </div>
  )
}

function IconShoppingTag() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
      <line x1="7" y1="7" x2="7.01" y2="7"/>
    </svg>
  )
}

function IconBanknote() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/>
      <path d="M6 12h.01M18 12h.01"/>
    </svg>
  )
}

function IconAlertTriangle() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 1 1.71 3h16.94a2 2 0 0 1 1.71-3L13.71 3.86a2 2 0 0 1-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  )
}

function IconCheckCircle() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
    </svg>
  )
}

const MODES = [
  { id: 'listing', label: 'Listing Anomaly Scoring', desc: 'Product price & seller verification', icon: <IconShoppingTag /> },
  { id: 'currency', label: 'Currency Note Scan', desc: '₹100, ₹200, ₹500 visual check', icon: <IconBanknote /> },
]

const RUPEE_DENOMINATIONS = [
  { value: '500', label: '₹500 Rupee Note (Stone Grey - Red Fort Motif)' },
  { value: '200', label: '₹200 Rupee Note (Bright Yellow - Sanchi Stupa)' },
  { value: '100', label: '₹100 Rupee Note (Lavender - Rani ki Vav)' },
]

const MARKETPLACES = ['Amazon', 'Flipkart', 'Meesho', 'IndiaMart', 'eBay', 'Shopify', 'Other']

const PRESETS = [
  {
    name: 'Counterfeit ₹500 Note',
    denomination: '500',
    brand: 'Reserve Bank of India',
    price: 0,
    rrp: 500,
    marketplace: 'Currency Scan',
    riskTag: 'SUSPICIOUS NOTE',
    tagColor: '#f43f5e',
    icon: <IconBanknote />,
    mode: 'currency',
  },
  {
    name: 'Rolex Submariner 1:1',
    denomination: '500',
    brand: 'Rolex',
    price: 49.99,
    rrp: 12500,
    marketplace: 'Amazon',
    riskTag: 'CRITICAL REPLICA',
    tagColor: '#f43f5e',
    icon: <IconAlertTriangle />,
    mode: 'listing',
  },
  {
    name: 'Counterfeit ₹200 Note',
    denomination: '200',
    brand: 'Reserve Bank of India',
    price: 0,
    rrp: 200,
    marketplace: 'Currency Scan',
    riskTag: 'HIGH RISK NOTE',
    tagColor: '#f97316',
    icon: <IconBanknote />,
    mode: 'currency',
  },
  {
    name: 'Genuine ₹100 Note',
    denomination: '100',
    brand: 'Reserve Bank of India',
    price: 0,
    rrp: 100,
    marketplace: 'Currency Scan',
    riskTag: 'GENUINE NOTE',
    tagColor: '#10b981',
    icon: <IconCheckCircle />,
    mode: 'currency',
  },
]

export default function Counterfeit() {
  const [activeMode, setActiveMode] = useState<'listing' | 'currency'>('listing')
  
  // Listing fields
  const [productName, setProductName] = useState('Luxury Watch Replica 1:1')
  const [brand, setBrand] = useState('Rolex')
  const [price, setPrice] = useState(49.99)
  const [expectedPrice, setExpectedPrice] = useState(12500)
  const [marketplace, setMarketplace] = useState('Amazon')
  
  // Currency fields
  const [denomination, setDenomination] = useState('500')
  const [currencyFile, setCurrencyFile] = useState<File | null>(null)
  const [currencyFileName, setCurrencyFileName] = useState<string | null>(null)
  
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CounterfeitResult | null>(null)
  const [currencyScanResult, setCurrencyScanResult] = useState<CurrencyScanResponse | null>(null)

  function handlePresetSelect(p: typeof PRESETS[0]) {
    setActiveMode(p.mode as 'listing' | 'currency')
    setProductName(p.name)
    setBrand(p.brand)
    setPrice(p.price)
    setExpectedPrice(p.rrp)
    setMarketplace(p.marketplace)
    setDenomination(p.denomination)
    setResult(null)
    setCurrencyScanResult(null)
    setError(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null); setResult(null); setCurrencyScanResult(null)
    try {
      if (activeMode === 'currency') {
        if (currencyFile) {
          // Real Computer Vision scan via backend POST /api/counterfeit/scan
          const scanRes = await scanCurrencyNote(currencyFile)
          setCurrencyScanResult(scanRes)
        } else {
          // Simulated/Preset scan for selected Rupee note
          const simulatedPayload = `[₹${denomination} Note Scan] ${productName} (RBI Security Verification)`
          const data = await analyzeCounterfeit(simulatedPayload, 'Reserve Bank of India', Number(denomination), 'Currency Note Scan')
          setResult(data as CounterfeitResult)
        }
      } else {
        const data = await analyzeCounterfeit(productName, brand, price, marketplace)
        setResult(data as CounterfeitResult)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setBusy(false)
    }
  }

  function handleCurrencyUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setCurrencyFile(file)
    setCurrencyFileName(file.name)
    setProductName(`₹${denomination} Note Scan (${file.name})`)
    setBrand('Reserve Bank of India')
  }

  const priceDiscountPct = expectedPrice > 0 && price > 0 ? Math.round(((expectedPrice - price) / expectedPrice) * 100) : 0

  return (
    <div className="animate-fade-in" style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* Page Header */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              Counterfeit Product & Currency Analysis Studio
            </h2>
            <RiskBadge level="medium" label="₹100 / ₹200 / ₹500 Scan" />
          </div>
          <p style={{ margin: '0.2rem 0 0', color: 'var(--text-secondary)', fontSize: '0.8125rem', fontWeight: 400 }}>
            Detect replica goods, price anomalies, and analyze ₹100, ₹200, and ₹500 rupee notes for counterfeit security cues.
          </p>
        </div>

        {/* Eye-Catching Threat Launchers */}
        <div>
          <p className="section-label" style={{ marginBottom: '0.45rem' }}>Featured Scenario Presets (Click to Test)</p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '0.75rem',
          }}>
            {PRESETS.map((p, idx) => (
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
                    {p.icon}
                    <span style={{ fontSize: '0.82rem', fontWeight: 700 }}>{p.name}</span>
                  </div>
                  <span style={{
                    fontSize: '0.62rem', fontWeight: 700, color: p.tagColor,
                    padding: '0.1rem 0.4rem', background: 'var(--bg-elevated)',
                    borderRadius: 6, border: `1px solid ${p.tagColor}`
                  }}>
                    {p.riskTag}
                  </span>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 400 }}>
                  {p.mode === 'currency' ? `₹${p.denomination} Note` : `${p.brand} · $${p.price}`} ({p.marketplace})
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Mode Filter Chips ─────────────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '0.75rem',
      }}>
        {MODES.map(m => (
          <button
            key={m.id}
            type="button"
            onClick={() => {
              setActiveMode(m.id as 'listing' | 'currency')
              setResult(null)
              setCurrencyScanResult(null)
              setError(null)
            }}
            className="glass-card"
            style={{
              padding: '0.8rem 1rem',
              borderRadius: 10,
              cursor: 'pointer',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              background: activeMode === m.id ? 'var(--nav-active-bg)' : 'var(--card-bg)',
              color: activeMode === m.id ? 'var(--nav-active-text)' : 'var(--text-primary)',
              border: activeMode === m.id ? '1px solid var(--nav-active-bg)' : '1px solid var(--border-subtle)',
              transition: 'all 0.15s ease',
            }}
          >
            <div style={{ opacity: activeMode === m.id ? 1 : 0.75 }}>{m.icon}</div>
            <div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, lineHeight: 1.2 }}>{m.label}</div>
              <div style={{ fontSize: '0.68rem', color: activeMode === m.id ? 'var(--nav-active-text)' : 'var(--text-muted)', fontWeight: 400, opacity: 0.85 }}>
                {m.desc}
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* ── 2-Column Full Width Studio Layout ────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
        gap: '1.25rem',
        alignItems: 'flex-start',
      }}>
        
        {/* Left Column: Form Inputs */}
        <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            
            {activeMode === 'listing' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div>
                  <label className="section-label" htmlFor="product-name">Product Title / Listing Name</label>
                  <input
                    id="product-name"
                    className="input-field"
                    value={productName}
                    onChange={e => setProductName(e.target.value)}
                    placeholder="e.g. Luxury Watch Replica 1:1"
                    style={{ borderRadius: 8, fontWeight: 400 }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="section-label" htmlFor="brand">Brand Name</label>
                    <input
                      id="brand"
                      className="input-field"
                      value={brand}
                      onChange={e => setBrand(e.target.value)}
                      placeholder="Rolex, Apple, Nike"
                      style={{ borderRadius: 8, fontWeight: 400 }}
                    />
                  </div>
                  <div>
                    <label className="section-label" htmlFor="marketplace">E-Commerce Platform</label>
                    <select
                      id="marketplace"
                      className="input-field"
                      value={marketplace}
                      onChange={e => setMarketplace(e.target.value)}
                      style={{ borderRadius: 8, fontWeight: 400 }}
                    >
                      {MARKETPLACES.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="section-label" htmlFor="price">Listed Price (USD $)</label>
                    <input
                      id="price"
                      type="number"
                      step="0.01"
                      className="input-field"
                      value={price}
                      onChange={e => setPrice(Number(e.target.value))}
                      placeholder="49.99"
                      style={{ borderRadius: 8, fontWeight: 400 }}
                    />
                  </div>
                  <div>
                    <label className="section-label" htmlFor="expected-price">Official Market RRP ($)</label>
                    <input
                      id="expected-price"
                      type="number"
                      step="0.01"
                      className="input-field"
                      value={expectedPrice}
                      onChange={e => setExpectedPrice(Number(e.target.value))}
                      placeholder="12500.00"
                      style={{ borderRadius: 8, fontWeight: 400 }}
                    />
                  </div>
                </div>

                {priceDiscountPct > 0 && (
                  <div style={{ padding: '0.65rem 0.85rem', background: 'var(--bg-elevated)', borderRadius: 8, fontSize: '0.78rem', color: priceDiscountPct > 60 ? '#f43f5e' : 'var(--text-secondary)', fontWeight: 400, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span>Price Anomaly Delta:</span>
                    <span style={{ fontWeight: 700 }}>{priceDiscountPct}% below Official Market Price</span>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                
                {/* Denomination Dropdown */}
                <div>
                  <label className="section-label" htmlFor="rupee-denomination">Rupee Note Denomination</label>
                  <select
                    id="rupee-denomination"
                    className="input-field"
                    value={denomination}
                    onChange={e => {
                      const d = e.target.value
                      setDenomination(d)
                      setProductName(`₹${d} Rupee Note Scan`)
                    }}
                    style={{ borderRadius: 8, fontWeight: 400 }}
                  >
                    {RUPEE_DENOMINATIONS.map(d => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="section-label" htmlFor="currency-name">Note Verification Identifier</label>
                  <input
                    id="currency-name"
                    className="input-field"
                    value={productName}
                    onChange={e => setProductName(e.target.value)}
                    placeholder="e.g. ₹500 Note Serial Check"
                    style={{ borderRadius: 8, fontWeight: 400 }}
                  />
                </div>

                {/* Currency Dropzone */}
                <div style={{
                  padding: '1.25rem',
                  border: '1px dashed var(--border-default)',
                  borderRadius: 10, background: 'var(--bg-elevated)',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
                  textAlign: 'center'
                }}>
                  <IconBanknote />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 400 }}>
                    {currencyFileName ? `Uploaded Image: ${currencyFileName}` : `Upload ₹${denomination} Note Image (JPEG / PNG)`}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    Scans RBI security thread, micro-print text, Mahatma Gandhi portrait watermark & serial numbers
                  </span>
                  <label className="btn-secondary" style={{ cursor: 'pointer', margin: '0.4rem 0 0', fontSize: '0.78rem', borderRadius: 8, fontWeight: 400 }}>
                    Select ₹{denomination} Note Image
                    <input type="file" accept="image/jpeg,image/png" onChange={handleCurrencyUpload} style={{ display: 'none' }} />
                  </label>
                </div>
              </div>
            )}

            <button className="btn-primary" disabled={busy || !productName.trim()} style={{ borderRadius: 8, fontWeight: 400, marginTop: '0.5rem', minHeight: 38 }}>
              {busy ? <span className="spinner" /> : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              )}
              {busy ? 'Evaluating Authenticity...' : activeMode === 'currency' ? `Run ₹${denomination} Note Verification` : 'Score Listing Authenticity'}
            </button>
          </form>

          {error && (
            <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: 'var(--bg-elevated)', border: '1px solid #f43f5e', borderRadius: 8, color: '#f43f5e', fontSize: '0.85rem', fontWeight: 400 }}>
              Error: {error}
            </div>
          )}
        </div>

        {/* Right Column: Output Results */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {/* Currency Scan Response (Real Computer Vision output) */}
          {currencyScanResult ? (
            <div className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                  <AuthenticityGauge score={1 - currencyScanResult.confidence} />
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.6rem' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>₹{denomination} Note Verdict</span>
                      <RiskBadge
                        level={currencyScanResult.verdict === 'counterfeit' ? 'critical' : currencyScanResult.verdict === 'uncertain' ? 'medium' : 'low'}
                        label={currencyScanResult.verdict.toUpperCase()}
                      />
                    </div>
                    <p style={{ margin: '0 0 0.85rem', fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, fontWeight: 400 }}>
                      {currencyScanResult.recommended_action}
                    </p>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                      Model: {currencyScanResult.model_version} · Audit ID: {currencyScanResult.audit_event_id?.slice(0, 8)}...
                    </span>
                  </div>
                </div>
              </div>

              {/* Region Scores Breakdown */}
              <div className="glass-card" style={{ padding: '1.25rem', borderRadius: 10 }}>
                <p className="section-label">RBI Security Feature Region Cues (OpenCV)</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                      <span>Security Thread Integrity</span>
                      <span>{Math.round(currencyScanResult.region_scores.security_thread * 100)}%</span>
                    </div>
                    <div style={{ height: 5, background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{ width: `${currencyScanResult.region_scores.security_thread * 100}%`, height: '100%', background: currencyScanResult.region_scores.security_thread > 0.6 ? '#f43f5e' : '#10b981' }} />
                    </div>
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                      <span>Micro-print Text Quality</span>
                      <span>{Math.round(currencyScanResult.region_scores.microprint * 100)}%</span>
                    </div>
                    <div style={{ height: 5, background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{ width: `${currencyScanResult.region_scores.microprint * 100}%`, height: '100%', background: currencyScanResult.region_scores.microprint > 0.6 ? '#f43f5e' : '#10b981' }} />
                    </div>
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                      <span>Serial Number Alignment</span>
                      <span>{Math.round(currencyScanResult.region_scores.serial_number * 100)}%</span>
                    </div>
                    <div style={{ height: 5, background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{ width: `${currencyScanResult.region_scores.serial_number * 100}%`, height: '100%', background: currencyScanResult.region_scores.serial_number > 0.6 ? '#f43f5e' : '#10b981' }} />
                    </div>
                  </div>
                </div>
              </div>

              <JsonViewer data={currencyScanResult} title="Payload & Technical Config" defaultOpen={false} />
            </div>
          ) : result ? (
            <div className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                  <AuthenticityGauge score={result.authenticity_score} />
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.6rem' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                        {activeMode === 'currency' ? `₹${denomination} Note Verdict` : 'Authenticity Status'}
                      </span>
                      <RiskBadge level={result.risk_level} />
                    </div>
                    <p style={{ margin: '0 0 0.85rem', fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, fontWeight: 400 }}>
                      {result.explanation}
                    </p>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                      Model: {result.model_version} · Audit ID: {result.request_id.slice(0, 8)}...
                    </span>
                  </div>
                </div>
              </div>

              {result.red_flags && result.red_flags.length > 0 && (
                <div className="glass-card" style={{ padding: '1.25rem', borderRadius: 10 }}>
                  <p className="section-label">Detected Replica & Security Indicators</p>
                  <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                    {result.red_flags.map((flag, i) => (
                      <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.55rem', fontSize: '0.8375rem', color: 'var(--text-secondary)', fontWeight: 400 }}>
                        <span style={{ color: '#f43f5e', marginTop: '0.1rem', flexShrink: 0 }}>•</span>
                        {flag}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <JsonViewer data={result} title="Payload & Technical Config" defaultOpen={false} />
            </div>
          ) : (
            <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {activeMode === 'currency' ? `₹${denomination} Note RBI Security Cues` : 'Replica Signal Radar'}
                  </h3>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    {activeMode === 'currency' ? 'Computer Vision checks for security thread & micro-print' : 'Active authenticity rules evaluated by model'}
                  </span>
                </div>
                <span className="tag" style={{ fontSize: '0.7rem' }}>Ready for input</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 8 }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.2rem', fontWeight: 400 }}>
                    {activeMode === 'currency' ? 'Denominations Supported' : 'Price Delta Check'}
                  </div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {activeMode === 'currency' ? '₹100, ₹200, ₹500 Notes' : 'Deep Discount Threshold'}
                  </div>
                </div>
                <div style={{ padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 8 }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.2rem', fontWeight: 400 }}>
                    {activeMode === 'currency' ? 'OpenCV Feature Pipeline' : 'Keywords Checked'}
                  </div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {activeMode === 'currency' ? 'Thread, Micro-print & Serial' : '"Replica 1:1", "AAA Quality"'}
                  </div>
                </div>
              </div>

              <div style={{ padding: '0.85rem 1rem', background: 'var(--bg-elevated)', borderRadius: 8, borderLeft: '3px solid #10b981', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <span style={{ fontSize: '0.8rem', fontWeight: 400, color: 'var(--text-primary)', display: 'block' }}>
                    {activeMode === 'currency' ? `Run ₹${denomination} Note Verification` : 'Quick Authenticity Test'}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    Click button to evaluate security features
                  </span>
                </div>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={(e) => void handleSubmit(e as unknown as FormEvent)}
                  style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem', borderRadius: 6 }}
                >
                  Score Now
                </button>
              </div>
            </div>
          )}
        </div>

      </div>

    </div>
  )
}

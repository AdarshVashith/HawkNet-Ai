import { useEffect, useRef, useState, type FormEvent } from 'react'
import { analyzeGeospatial, getGeospatialHotspots } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import JsonViewer from '../components/JsonViewer'

type GeoResult = {
  request_id: string
  risk_level: string
  risk_score: number
  hotspots_nearby: number
  recommendations: string[]
  explanation: string
  model_version: string
  region_label?: string
}

type DistrictHotspot = {
  district: string
  state: string
  risk_score: number
  priority_rank: number
  latitude: number
  longitude: number
  primary_threat: string
}

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
          <span style={{ fontSize: '0.58rem', color: 'var(--text-muted)', fontWeight: 400, textTransform: 'uppercase', letterSpacing: '0.05em' }}>risk score</span>
        </div>
      </div>
      <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 400 }}>Geospatial Threat Rating</span>
    </div>
  )
}

function IconMapPin() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
    </svg>
  )
}

function IconCrosshair() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/>
    </svg>
  )
}

const CATEGORIES = ['general', 'scam', 'theft', 'violence', 'cyber', 'counterfeit']

const CITY_PRESETS = [
  { name: 'New Delhi (Connaught Place)', lat: 28.6139, lng: 77.2090, tag: 'NCR HUB', color: '#f59e0b', threat: 'ATM & Phishing Scams' },
  { name: 'Mewat / Nuh Cyber Hub', lat: 28.1023, lng: 77.0142, tag: 'HIGH RISK HUB', color: '#f43f5e', threat: 'Sextortion & OTP Fraud' },
  { name: 'Jamtara Cyber Belt', lat: 23.9627, lng: 86.8021, tag: 'CRITICAL RISK', color: '#f43f5e', threat: 'Bank Impersonation' },
  { name: 'Bengaluru Tech Corridor', lat: 12.9716, lng: 77.5946, tag: 'SAFE TECH BELT', color: '#10b981', threat: 'Crypto & Job Scams' },
  { name: 'Mumbai Financial Zone', lat: 19.0760, lng: 72.8777, tag: 'MODERATE RISK', color: '#f59e0b', threat: 'Investment Fraud' },
]

export default function Geospatial() {
  const [lat, setLat] = useState(28.6139)
  const [lng, setLng] = useState(77.2090)
  const [radius, setRadius] = useState(5)
  const [category, setCategory] = useState('general')
  const [locating, setLocating] = useState(false)
  
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GeoResult | null>(null)

  const [hotspots, setHotspots] = useState<DistrictHotspot[]>([])
  const [loadingHotspots, setLoadingHotspots] = useState(true)

  const mapContainerRef = useRef<HTMLDivElement | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapInstanceRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markerRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const circleRef = useRef<any>(null)

  // Auto-detect user's current GPS location on mount
  useEffect(() => {
    locateUser()
    getGeospatialHotspots()
      .then(res => {
        if (res?.hotspots) setHotspots(res.hotspots)
      })
      .catch(() => {})
      .finally(() => setLoadingHotspots(false))
  }, [])

  function locateUser() {
    if (!('geolocation' in navigator)) return
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const userLat = parseFloat(pos.coords.latitude.toFixed(4))
        const userLng = parseFloat(pos.coords.longitude.toFixed(4))
        setLat(userLat)
        setLng(userLng)
        setLocating(false)
      },
      () => {
        setLocating(false)
      },
      { timeout: 6000, enableHighAccuracy: true }
    )
  }

  // Load Leaflet dynamically for real-life interactive OpenStreetMap tiles
  useEffect(() => {
    let active = true

    async function initLeafletMap() {
      if (!mapContainerRef.current) return
      
      if (!document.getElementById('leaflet-css')) {
        const link = document.createElement('link')
        link.id = 'leaflet-css'
        link.rel = 'stylesheet'
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
        document.head.appendChild(link)
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if (!(window as any).L) {
        const script = document.createElement('script')
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
        script.onload = () => {
          if (active) renderMap()
        }
        document.head.appendChild(script)
      } else {
        renderMap()
      }
    }

    function renderMap() {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const L = (window as any).L
      if (!L || !mapContainerRef.current) return

      if (!mapInstanceRef.current) {
        const map = L.map(mapContainerRef.current).setView([lat, lng], 13)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map)

        const marker = L.marker([lat, lng], { draggable: true }).addTo(map)
        const circle = L.circle([lat, lng], {
          color: '#f43f5e',
          fillColor: '#f43f5e',
          fillOpacity: 0.15,
          radius: radius * 1000,
        }).addTo(map)

        marker.on('dragend', () => {
          const pos = marker.getLatLng()
          const newLat = parseFloat(pos.lat.toFixed(4))
          const newLng = parseFloat(pos.lng.toFixed(4))
          setLat(newLat)
          setLng(newLng)
          circle.setLatLng(pos)
        })

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        map.on('click', (e: any) => {
          const newLat = parseFloat(e.latlng.lat.toFixed(4))
          const newLng = parseFloat(e.latlng.lng.toFixed(4))
          setLat(newLat)
          setLng(newLng)
          marker.setLatLng(e.latlng)
          circle.setLatLng(e.latlng)
        })

        mapInstanceRef.current = map
        markerRef.current = marker
        circleRef.current = circle
      } else {
        mapInstanceRef.current.setView([lat, lng], 13)
        if (markerRef.current) markerRef.current.setLatLng([lat, lng])
        if (circleRef.current) {
          circleRef.current.setLatLng([lat, lng])
          circleRef.current.setRadius(radius * 1000)
        }
      }
    }

    void initLeafletMap()

    return () => {
      active = false
    }
  }, [lat, lng, radius])

  function handleCitySelect(c: typeof CITY_PRESETS[0]) {
    setLat(c.lat)
    setLng(c.lng)
    setResult(null)
    setError(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null); setResult(null)
    try {
      const data = await analyzeGeospatial(lat, lng, radius, category)
      setResult(data as GeoResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="animate-fade-in" style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* Page Header */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              Geospatial Crime & Hotspot Intelligence Studio
            </h2>
            <RiskBadge level="medium" label="OpenStreetMap GIS" />
          </div>
          <p style={{ margin: '0.2rem 0 0', color: 'var(--text-secondary)', fontSize: '0.8125rem', fontWeight: 400 }}>
            Real-time interactive OpenStreetMap GIS vector map initialized to your location. Drag marker or click anywhere to score local crime risk.
          </p>
        </div>

        {/* Featured City Presets */}
        <div>
          <p className="section-label" style={{ marginBottom: '0.45rem' }}>Featured Cyber Crime Hotspots (Click to Jump)</p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '0.75rem',
          }}>
            {CITY_PRESETS.map((c, idx) => (
              <button
                key={idx}
                type="button"
                className="glass-card"
                onClick={() => handleCitySelect(c)}
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
                    <IconMapPin />
                    <span style={{ fontSize: '0.82rem', fontWeight: 700 }}>{c.name}</span>
                  </div>
                  <span style={{
                    fontSize: '0.62rem', fontWeight: 700, color: c.color,
                    padding: '0.1rem 0.4rem', background: 'var(--bg-elevated)',
                    borderRadius: 6, border: `1px solid ${c.color}`
                  }}>
                    {c.tag}
                  </span>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 400 }}>
                  {c.lat}, {c.lng} ({c.threat})
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
        
        {/* Left Column: Real OpenStreetMap Interactive Canvas & Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {/* Interactive OpenStreetMap Tile Canvas */}
          <div className="glass-card" style={{ padding: '0.5rem', borderRadius: 10, overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.5rem 0.75rem', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <IconMapPin /> Live OpenStreetMap Vector Canvas
              </span>
              <button
                type="button"
                className="btn-secondary"
                disabled={locating}
                onClick={locateUser}
                style={{ padding: '0.2rem 0.6rem', fontSize: '0.72rem', borderRadius: 6, display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 400 }}
              >
                <IconCrosshair />
                {locating ? 'Locating...' : 'Locate Me'}
              </button>
            </div>
            <div
              ref={mapContainerRef}
              style={{
                width: '100%',
                height: 320,
                borderRadius: 8,
                marginTop: '0.5rem',
                background: 'var(--bg-elevated)',
                position: 'relative',
                zIndex: 1,
              }}
            />
          </div>

          {/* Location Controls Form */}
          <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem' }}>
                <div>
                  <label className="section-label" htmlFor="geo-lat">Latitude</label>
                  <input
                    id="geo-lat"
                    type="number"
                    step="any"
                    className="input-field"
                    value={lat}
                    onChange={e => setLat(Number(e.target.value))}
                    placeholder="28.6139"
                    style={{ borderRadius: 8, fontWeight: 400 }}
                  />
                </div>
                <div>
                  <label className="section-label" htmlFor="geo-lng">Longitude</label>
                  <input
                    id="geo-lng"
                    type="number"
                    step="any"
                    className="input-field"
                    value={lng}
                    onChange={e => setLng(Number(e.target.value))}
                    placeholder="77.2090"
                    style={{ borderRadius: 8, fontWeight: 400 }}
                  />
                </div>
              </div>

              <div>
                <label className="section-label" htmlFor="geo-radius" style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Search Radius</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{radius} km</span>
                </label>
                <input
                  id="geo-radius"
                  type="range" min={1} max={50} step={1}
                  value={radius}
                  onChange={e => setRadius(Number(e.target.value))}
                  style={{
                    width: '100%', height: 5,
                    appearance: 'none', background: 'var(--border-default)',
                    borderRadius: 4, border: 'none', cursor: 'pointer', outline: 'none',
                    marginTop: '0.4rem',
                  }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.25rem', fontWeight: 400 }}>
                  <span>1 km</span><span>25 km</span><span>50 km</span>
                </div>
              </div>

              <div>
                <label className="section-label" htmlFor="geo-category">Crime & Fraud Category Filter</label>
                <select
                  id="geo-category"
                  className="input-field"
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  style={{ borderRadius: 8, fontWeight: 400 }}
                >
                  {CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
              </div>

              <button className="btn-primary" disabled={busy} style={{ borderRadius: 8, fontWeight: 400, minHeight: 38 }}>
                {busy ? <span className="spinner" /> : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                )}
                {busy ? 'Evaluating Geospatial Model...' : `Score Risk at Lat ${lat}, Lng ${lng}`}
              </button>
            </form>

            {error && (
              <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: 'var(--bg-elevated)', border: '1px solid #f43f5e', borderRadius: 8, color: '#f43f5e', fontSize: '0.85rem', fontWeight: 400 }}>
                Error: {error}
              </div>
            )}
          </div>

        </div>

        {/* Right Column: Intelligence Output & Results */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {result ? (
            <div className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                  <RiskGauge score={result.risk_score} />
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.6rem' }}>
                      <RiskBadge level={result.risk_level} />
                      {result.region_label && (
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 400 }}>Region: {result.region_label}</span>
                      )}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.65rem', marginBottom: '0.85rem' }}>
                      <div style={{ padding: '0.65rem', background: 'var(--bg-elevated)', borderRadius: 8 }}>
                        <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)' }}>{result.hotspots_nearby}</div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 400 }}>Hotspots Within Radius</div>
                      </div>
                      <div style={{ padding: '0.65rem', background: 'var(--bg-elevated)', borderRadius: 8 }}>
                        <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)' }}>{radius} km</div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 400 }}>Search Radius</div>
                      </div>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, fontWeight: 400 }}>{result.explanation}</p>
                  </div>
                </div>
              </div>

              {result.recommendations && result.recommendations.length > 0 && (
                <div className="glass-card" style={{ padding: '1.25rem', borderRadius: 10 }}>
                  <p className="section-label">Public Safety Patrol Recommendations</p>
                  <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                    {result.recommendations.map((rec, i) => (
                      <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.55rem', fontSize: '0.8375rem', color: 'var(--text-secondary)', fontWeight: 400 }}>
                        <span style={{ color: '#10b981', marginTop: '0.1rem', flexShrink: 0 }}>•</span>
                        {rec}
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
                    NCRB Cyber Crime District Leaderboard
                  </h3>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    Official Published District Hotspot Rankings
                  </span>
                </div>
                <span className="tag" style={{ fontSize: '0.7rem' }}>Live Database</span>
              </div>

              {loadingHotspots ? (
                <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: 28 }} />)}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                  {hotspots.slice(0, 5).map(h => (
                    <div
                      key={h.district}
                      onClick={() => {
                        setLat(h.latitude)
                        setLng(h.longitude)
                      }}
                      style={{
                        padding: '0.6rem 0.8rem',
                        background: 'var(--bg-elevated)',
                        borderRadius: 8,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div>
                        <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block' }}>
                          #{h.priority_rank} {h.district}, {h.state}
                        </span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                          Primary threat: {h.primary_threat}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.82rem', fontWeight: 700, color: h.risk_score > 0.7 ? '#f43f5e' : '#f59e0b' }}>
                        {Math.round(h.risk_score * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ marginTop: '1rem', padding: '0.85rem 1rem', background: 'var(--bg-elevated)', borderRadius: 8, borderLeft: '3px solid #10b981', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <span style={{ fontSize: '0.8rem', fontWeight: 400, color: 'var(--text-primary)', display: 'block' }}>
                    Run Geospatial Analysis
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    Click button to score selected coordinates on map
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

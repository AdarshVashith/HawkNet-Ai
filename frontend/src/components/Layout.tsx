import { NavLink, useLocation } from 'react-router-dom'
import { useEffect, useState, type ReactNode } from 'react'
import StatusDot from './StatusDot'
import { getHealth, type HealthResponse } from '../lib/api'

function IconDashboard() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
  )
}
function IconShield() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  )
}
function IconTag() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
      <line x1="7" y1="7" x2="7.01" y2="7"/>
    </svg>
  )
}
function IconGraph() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3"/>
      <circle cx="6" cy="12" r="3"/>
      <circle cx="18" cy="19" r="3"/>
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
    </svg>
  )
}
function IconMap() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
      <line x1="9" y1="3" x2="9" y2="18"/>
      <line x1="15" y1="6" x2="15" y2="21"/>
    </svg>
  )
}
function IconUser() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  )
}
function IconClipboard() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>
    </svg>
  )
}
function IconAlert() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--bg-base)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  )
}
function IconSun() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  )
}
function IconMoon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  )
}

interface NavItem {
  to: string
  label: string
  icon: ReactNode
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard',      label: 'Dashboard',       icon: <IconDashboard /> },
  { to: '/scam-detection', label: 'Scam Detection',  icon: <IconShield /> },
  { to: '/counterfeit',    label: 'Counterfeit',      icon: <IconTag /> },
  { to: '/fraud-graph',    label: 'Fraud Graph',      icon: <IconGraph /> },
  { to: '/geospatial',     label: 'Geospatial',       icon: <IconMap /> },
  { to: '/citizen-shield', label: 'Citizen Shield',   icon: <IconUser /> },
  { to: '/audit',          label: 'Audit Log',        icon: <IconClipboard /> },
]

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthStatus, setHealthStatus] = useState<'ok' | 'error' | 'loading'>('loading')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('app-theme') as 'dark' | 'light') || 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('app-theme', theme)
  }, [theme])

  useEffect(() => {
    let mounted = true
    let retryCount = 0
    const MAX_RETRIES = 8
    const RETRY_DELAYS = [1000, 2000, 4000, 8000, 15000, 20000, 30000, 30000]

    async function check() {
      try {
        const data = await getHealth()
        if (mounted) {
          setHealth(data)
          setHealthStatus('ok')
          retryCount = 0
          // Keep polling every 30s after success
          setTimeout(check, 30000)
        }
      } catch {
        if (!mounted) return
        setHealthStatus('error')
        if (retryCount < MAX_RETRIES) {
          const delay = RETRY_DELAYS[retryCount] ?? 30000
          retryCount++
          setTimeout(check, delay)
        } else {
          // Give up retrying fast, but still check every 60s
          setTimeout(check, 60000)
        }
      }
    }

    setHealthStatus('loading')
    check()
    return () => { mounted = false }
  }, [])


  useEffect(() => { setMobileOpen(false) }, [location.pathname])

  const current = NAV_ITEMS.find(n => n.to === location.pathname)

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-base)', color: 'var(--text-primary)' }}>
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
            zIndex: 40,
          }}
        />
      )}

      {/* ── Sidebar ────────────────────────────────────── */}
      <aside
        style={{
          position: 'fixed',
          top: 0, left: 0, bottom: 0,
          width: 'var(--sidebar-width)',
          background: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 50,
          transform: mobileOpen ? 'translateX(0)' : undefined,
          transition: 'transform 0.2s ease',
        }}
      >
        {/* Logo */}
        <div style={{
          padding: '1.25rem 1rem 1rem',
          borderBottom: '1px solid var(--border-subtle)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.2rem' }}>
            <div style={{
              width: 30, height: 30,
              borderRadius: 6,
              background: 'var(--text-primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <IconAlert />
            </div>
            <h1 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              HawkNet-Ai
            </h1>
          </div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', paddingLeft: '2.4rem', margin: 0, fontWeight: 400 }}>
            Public Safety Intelligence
          </p>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '0.75rem 0.6rem', overflowY: 'auto' }}>
          <p className="section-label" style={{ paddingLeft: '0.25rem', marginTop: '0.5rem' }}>Modules</p>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                >
                  <span className="nav-icon">{item.icon}</span>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* API Status */}
        <div style={{
          padding: '0.85rem 1rem',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
        }}>
          <StatusDot status={healthStatus} />
          <div style={{ minWidth: 0 }}>
            <p style={{ margin: 0, fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-primary)' }}>
              {healthStatus === 'ok' ? `API ${health?.status ?? ''}` : healthStatus === 'loading' ? 'Connecting...' : 'API unreachable'}
            </p>
            {health && (
              <p style={{ margin: 0, fontSize: '0.68rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 400 }}>
                {health.service} v{health.version}
              </p>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main Area ──────────────────────────────────── */}
      <div style={{
        marginLeft: 'var(--sidebar-width)',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minWidth: 0,
      }}>
        {/* Topbar */}
        <header style={{
          position: 'sticky', top: 0, zIndex: 30,
          height: 'var(--topbar-height)',
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          paddingInline: '1.5rem',
          gap: '1rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h1 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {current?.label ?? 'HawkNet-Ai Platform'}
            </h1>
            <span style={{
              fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400,
              padding: '0.15rem 0.55rem', background: 'var(--bg-elevated)',
              borderRadius: 6, border: '1px solid var(--border-subtle)',
              display: 'inline-flex', alignItems: 'center', gap: '0.35rem'
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
              v0.1.0 · Operational Command
            </span>
          </div>

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            {/* Apple Segmented Theme Switcher */}
            <div className="segmented-control">
              <button
                type="button"
                className={`segmented-btn ${theme === 'dark' ? 'active' : ''}`}
                onClick={() => setTheme('dark')}
              >
                <IconMoon /> Dark
              </button>
              <button
                type="button"
                className={`segmented-btn ${theme === 'light' ? 'active' : ''}`}
                onClick={() => setTheme('light')}
              >
                <IconSun /> Light
              </button>
            </div>

            <StatusDot status={healthStatus} label={healthStatus === 'ok' ? 'API Healthy' : healthStatus === 'loading' ? 'Connecting...' : 'Offline'} />
          </div>
        </header>

        {/* Page content */}
        <main style={{ flex: 1, padding: '1.25rem', overflowY: 'auto' }}>
          {children}
        </main>
      </div>
    </div>
  )
}

import { useState, type FormEvent, type ChangeEvent } from 'react'
import { analyzeScam, scoreScamChunk } from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import JsonViewer from '../components/JsonViewer'

type ScamResult = {
  request_id?: string
  risk_level: string
  risk_score: number
  explanation?: string
  model_version?: string
  labels?: string[]
  signals?: string[]
  matched_signals?: string[]
  recommend_action?: string
  cumulative_chars?: number
  alerted?: boolean
}

function CircularProgress({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.min(Math.max(value / max, 0), 1)
  const r = 42
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)

  const color =
    pct < 0.35 ? '#10b981'
    : pct < 0.65 ? '#f59e0b'
    : pct < 0.85 ? '#f97316'
    : '#f43f5e'

  return (
    <div style={{ position: 'relative', width: 110, height: 110 }}>
      <svg width="110" height="110" viewBox="0 0 110 110" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="55" cy="55" r={r} fill="none" stroke="var(--border-default)" strokeWidth="8"/>
        <circle
          cx="55" cy="55" r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: '1.4rem', fontWeight: 700, color, lineHeight: 1 }}>
          {Math.round(pct * 100)}%
        </span>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 400, textTransform: 'uppercase', letterSpacing: '0.05em' }}>risk score</span>
      </div>
    </div>
  )
}

function IconMic() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/>
    </svg>
  )
}
function IconSMS() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  )
}
function IconMail() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
      <polyline points="22,6 12,13 2,6"/>
    </svg>
  )
}
function IconChat() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
    </svg>
  )
}
function IconSocial() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
    </svg>
  )
}
function IconGlobe() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>
  )
}

function IconSiren() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  )
}
function IconKey() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7.5" cy="15.5" r="5.5"/><path d="M21 2l-9.6 9.6"/><path d="M15.5 7.5l3 3"/>
    </svg>
  )
}
function IconBox() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f97316" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
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

const CHANNELS = [
  { id: 'Voice', label: 'Voice Call', desc: 'Audio call recordings', icon: <IconMic /> },
  { id: 'SMS', label: 'SMS / Text', desc: 'Phishing texts & sender IDs', icon: <IconSMS /> },
  { id: 'Email', label: 'Email Header', desc: 'Phishing email headers', icon: <IconMail /> },
  { id: 'Chat', label: 'WhatsApp', desc: 'Chat exports & DM logs', icon: <IconChat /> },
  { id: 'Social', label: 'Social DM', desc: 'Instagram & X messages', icon: <IconSocial /> },
  { id: 'Web', label: 'Phishing URL', desc: 'Fake websites & domains', icon: <IconGlobe /> },
]

const DEMO_PRESETS = [
  {
    name: 'Digital Arrest Scam',
    channel: 'Voice',
    riskTag: 'CRITICAL',
    tagColor: '#f43f5e',
    icon: <IconSiren />,
    text: 'This is CBI and Enforcement Directorate officer calling. Your Aadhaar card is linked to a international drug trafficking case. You are under digital arrest. Stay on this video call and do not disconnect under any circumstances or police will raid your house.',
  },
  {
    name: 'Bank OTP Phishing',
    channel: 'SMS',
    riskTag: 'HIGH RISK',
    tagColor: '#f97316',
    icon: <IconKey />,
    text: 'URGENT: Your HDFC bank account is suspended due to unverified KYC. Click here immediately to verify OTP and unlock account: https://hdfc-kyc-verify.phish.site',
  },
  {
    name: 'Customs Parcel Extortion',
    channel: 'Voice',
    riskTag: 'MEDIUM RISK',
    tagColor: '#f59e0b',
    icon: <IconBox />,
    text: 'Hello, your parcel from UK contains illegal contraband items. Customs fine of 45,000 INR must be transferred via UPI to clear clearance certificate before 4 PM or legal action initiated.',
  },
  {
    name: 'Benign Call Transcript',
    channel: 'Voice',
    riskTag: 'SAFE',
    tagColor: '#10b981',
    icon: <IconCheckCircle />,
    text: 'Hi Mom, I reached office safely. Let us meet for dinner around 8 PM today.',
  },
]

export default function ScamDetection() {
  const [channel, setChannel] = useState('Voice')
  const [text, setText] = useState('This is CBI officer. You are under digital arrest. Stay on this video call.')
  
  // Dynamic channel specific fields
  const [senderId, setSenderId] = useState('+919876543210')
  const [emailSubject, setEmailSubject] = useState('URGENT: Verify Bank Account KYC')
  const [senderEmail, setSenderEmail] = useState('security@bank-verify.com')
  const [chatPlatform, setChatPlatform] = useState('WhatsApp')
  const [socialHandle, setSocialHandle] = useState('@invest_crypto_official')
  const [webUrl, setWebUrl] = useState('https://hdfc-kyc-verify.phish.site')
  
  const [attachedFileName, setAttachedFileName] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ScamResult | null>(null)

  const [streaming, setStreaming] = useState(false)
  const [streamChunks, setStreamChunks] = useState<Array<{ seq: number; text: string; res?: ScamResult }>>([])

  function handleChannelChange(newChannel: string) {
    setChannel(newChannel)
    setAttachedFileName(null)
    setError(null)
    setStreamChunks([])
    setResult(null)
    if (newChannel === 'SMS') {
      setText('URGENT: Your bank account is blocked due to KYC. Click http://phish.site')
    } else if (newChannel === 'Email') {
      setText('Dear Customer, your bank access will expire today unless you verify account credentials.')
    } else if (newChannel === 'Chat') {
      setText('Hello, I am HR manager from Amazon. We offer part time job earning 5000 INR per day.')
    } else if (newChannel === 'Social') {
      setText('Invest 10,000 INR in our guaranteed crypto trading bot and double money in 24 hours.')
    } else if (newChannel === 'Web') {
      setText('Official HDFC Bank Verification Portal - Enter netbanking password & OTP to continue.')
    } else {
      setText('This is CBI officer calling. You are under digital arrest.')
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null); setResult(null); setStreamChunks([])
    try {
      let fullPayload = text
      if (channel === 'SMS') fullPayload = `[Sender: ${senderId}] ${text}`
      else if (channel === 'Email') fullPayload = `[From: ${senderEmail}] [Subject: ${emailSubject}] ${text}`
      else if (channel === 'Chat') fullPayload = `[Platform: ${chatPlatform}] ${text}`
      else if (channel === 'Social') fullPayload = `[Handle: ${socialHandle}] ${text}`
      else if (channel === 'Web') fullPayload = `[URL: ${webUrl}] ${text}`

      const data = await analyzeScam(fullPayload, channel)
      setResult(data as ScamResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setBusy(false)
    }
  }

  function handleFileUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setAttachedFileName(file.name)
    if (channel === 'Voice') {
      setText(`[Audio File: ${file.name}] Transcribe: "This is Inspector Kumar calling from Cyber Police. You are under digital arrest."`)
    } else {
      setText(`[Attached File: ${file.name}] File content loaded for threat analysis.`)
    }
  }

  async function runCallStreamSimulation() {
    setStreaming(true); setError(null); setResult(null); setStreamChunks([])
    const callId = `call-demo-${Date.now()}`
    const chunks = [
      'Hello, this is regarding a package held at the customs office in your city.',
      'This is CBI and Enforcement Directorate. Your Aadhaar is linked to a crime. You are under digital arrest. Stay on this video call.',
      'Do not tell anyone including your family. Share the OTP sent to your phone and transfer the penalty amount via UPI immediately.',
    ]

    const history: Array<{ seq: number; text: string; res?: ScamResult }> = []
    for (let i = 0; i < chunks.length; i++) {
      const chunkText = chunks[i]
      try {
        const res = await scoreScamChunk(callId, i + 1, chunkText)
        const typedRes = res as unknown as ScamResult
        history.push({ seq: i + 1, text: chunkText, res: typedRes })
        setStreamChunks([...history])
        setResult(typedRes)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Stream error')
      }
      await new Promise(r => setTimeout(r, 1000))
    }
    setStreaming(false)
  }

  return (
    <div className="animate-fade-in" style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* ── Top Header Banner with Eye-Catching Launch Cards ─────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              Scam & Digital Threat Intelligence Studio
            </h2>
            <RiskBadge level="high" label="NLP Neural Pipeline" />
          </div>
          <p style={{ margin: '0.2rem 0 0', color: 'var(--text-secondary)', fontSize: '0.8125rem', fontWeight: 400 }}>
            Analyze suspect calls, phishing emails, SMS fraud, and fake web links. Select a quick launch preset or tab below.
          </p>
        </div>

        {/* Eye-Catching Threat Launchers (4 Featured Presets) */}
        <div>
          <p className="section-label" style={{ marginBottom: '0.45rem' }}>Quick Attack Scenarios (Click to Test)</p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '0.75rem',
          }}>
            {DEMO_PRESETS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                className="glass-card"
                onClick={() => {
                  handleChannelChange(p.channel)
                  setText(p.text)
                }}
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
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 400 }}>
                  {p.text}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Channel Selector Tabs (Filter Chips) ────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: '0.6rem',
      }}>
        {CHANNELS.map(ch => (
          <button
            key={ch.id}
            type="button"
            onClick={() => handleChannelChange(ch.id)}
            className="glass-card"
            style={{
              padding: '0.75rem 0.85rem',
              borderRadius: 10,
              cursor: 'pointer',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              background: channel === ch.id ? 'var(--nav-active-bg)' : 'var(--card-bg)',
              color: channel === ch.id ? 'var(--nav-active-text)' : 'var(--text-primary)',
              border: channel === ch.id ? '1px solid var(--nav-active-bg)' : '1px solid var(--border-subtle)',
              transition: 'all 0.15s ease',
            }}
          >
            <div style={{ opacity: channel === ch.id ? 1 : 0.75 }}>{ch.icon}</div>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, lineHeight: 1.2 }}>{ch.label}</div>
              <div style={{ fontSize: '0.68rem', color: channel === ch.id ? 'var(--nav-active-text)' : 'var(--text-muted)', fontWeight: 400, opacity: 0.85 }}>
                {ch.desc}
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
        
        {/* Left Column: Personalized Channel Input Form */}
        <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            
            {/* 🎤 VOICE CHANNEL ATTACHMENT */}
            {channel === 'Voice' && (
              <div style={{
                padding: '0.95rem 1rem',
                border: '1px dashed var(--border-default)',
                borderRadius: 10, background: 'var(--bg-elevated)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div style={{ padding: '0.5rem', background: 'var(--bg-surface)', borderRadius: 8, color: 'var(--text-primary)', display: 'flex' }}>
                    <IconMic />
                  </div>
                  <div>
                    <span style={{ fontSize: '0.85rem', fontWeight: 400, color: 'var(--text-primary)', display: 'block' }}>
                      Upload Audio Recording (.mp3, .wav, .m4a, .ogg)
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                      {attachedFileName ? `Selected: ${attachedFileName}` : 'Extract speech transcript to score digital arrest / extortion risk'}
                    </span>
                  </div>
                </div>
                <label className="btn-secondary" style={{ cursor: 'pointer', margin: 0, fontSize: '0.78rem', minHeight: 34, fontWeight: 400, borderRadius: 8 }}>
                  Attach Audio
                  <input type="file" accept="audio/*,.mp3,.wav,.m4a,.ogg" onChange={handleFileUpload} style={{ display: 'none' }} />
                </label>
              </div>
            )}

            {/* 💬 SMS CHANNEL INPUTS */}
            {channel === 'SMS' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div>
                  <label className="section-label" htmlFor="sms-sender">Sender Phone Number / Sender ID</label>
                  <input id="sms-sender" className="input-field" value={senderId} onChange={e => setSenderId(e.target.value)} placeholder="+919876543210 or HDFCBK" style={{ borderRadius: 8 }} />
                </div>
                <div style={{
                  padding: '0.85rem', border: '1px dashed var(--border-default)', borderRadius: 8, background: 'var(--bg-elevated)',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem'
                }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {attachedFileName ? `Attached SMS file: ${attachedFileName}` : 'Attach SMS Screenshot / Export File (.png, .txt)'}
                  </span>
                  <label className="btn-secondary" style={{ cursor: 'pointer', margin: 0, fontSize: '0.72rem', borderRadius: 6 }}>
                    Attach File
                    <input type="file" accept="image/*,.txt,.csv" onChange={handleFileUpload} style={{ display: 'none' }} />
                  </label>
                </div>
              </div>
            )}

            {/* 📧 EMAIL CHANNEL INPUTS */}
            {channel === 'Email' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label className="section-label" htmlFor="email-from">From (Sender Email)</label>
                    <input id="email-from" className="input-field" value={senderEmail} onChange={e => setSenderEmail(e.target.value)} placeholder="security@bank-verify.com" style={{ borderRadius: 8 }} />
                  </div>
                  <div>
                    <label className="section-label" htmlFor="email-subject">Subject Line</label>
                    <input id="email-subject" className="input-field" value={emailSubject} onChange={e => setEmailSubject(e.target.value)} placeholder="URGENT: Verify Account" style={{ borderRadius: 8 }} />
                  </div>
                </div>
                <div style={{
                  padding: '0.85rem', border: '1px dashed var(--border-default)', borderRadius: 8, background: 'var(--bg-elevated)',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem'
                }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {attachedFileName ? `Attached EML file: ${attachedFileName}` : 'Attach Email EML file or Screenshot (.eml, .png)'}
                  </span>
                  <label className="btn-secondary" style={{ cursor: 'pointer', margin: 0, fontSize: '0.72rem', borderRadius: 6 }}>
                    Attach EML / Screenshot
                    <input type="file" accept=".eml,.msg,image/*" onChange={handleFileUpload} style={{ display: 'none' }} />
                  </label>
                </div>
              </div>
            )}

            {/* 🗨 CHAT CHANNEL INPUTS */}
            {channel === 'Chat' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div>
                  <label className="section-label" htmlFor="chat-platform">Chat App Platform</label>
                  <select id="chat-platform" className="input-field" value={chatPlatform} onChange={e => setChatPlatform(e.target.value)} style={{ borderRadius: 8 }}>
                    <option value="WhatsApp">WhatsApp</option>
                    <option value="Telegram">Telegram</option>
                    <option value="Signal">Signal</option>
                  </select>
                </div>
                <div style={{
                  padding: '0.85rem', border: '1px dashed var(--border-default)', borderRadius: 8, background: 'var(--bg-elevated)',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem'
                }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {attachedFileName ? `Attached Chat Export: ${attachedFileName}` : 'Attach WhatsApp/Telegram Export (.txt, .png)'}
                  </span>
                  <label className="btn-secondary" style={{ cursor: 'pointer', margin: 0, fontSize: '0.72rem', borderRadius: 6 }}>
                    Attach Chat Log
                    <input type="file" accept=".txt,image/*" onChange={handleFileUpload} style={{ display: 'none' }} />
                  </label>
                </div>
              </div>
            )}

            {/* 📱 SOCIAL CHANNEL INPUTS */}
            {channel === 'Social' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div>
                  <label className="section-label" htmlFor="social-handle">Target Profile Handle / DM Link</label>
                  <input id="social-handle" className="input-field" value={socialHandle} onChange={e => setSocialHandle(e.target.value)} placeholder="@invest_crypto_official" style={{ borderRadius: 8 }} />
                </div>
                <div style={{
                  padding: '0.85rem', border: '1px dashed var(--border-default)', borderRadius: 8, background: 'var(--bg-elevated)',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem'
                }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {attachedFileName ? `Attached DM Screenshot: ${attachedFileName}` : 'Attach Social DM Screenshot (.png, .jpg)'}
                  </span>
                  <label className="btn-secondary" style={{ cursor: 'pointer', margin: 0, fontSize: '0.72rem', borderRadius: 6 }}>
                    Attach Screenshot
                    <input type="file" accept="image/*" onChange={handleFileUpload} style={{ display: 'none' }} />
                  </label>
                </div>
              </div>
            )}

            {/* 🌐 WEB / URL CHANNEL INPUTS */}
            {channel === 'Web' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div>
                  <label className="section-label" htmlFor="web-url">Suspicious Web Domain / Phishing URL</label>
                  <input id="web-url" className="input-field" value={webUrl} onChange={e => setWebUrl(e.target.value)} placeholder="https://hdfc-kyc-verify.phish.site" style={{ borderRadius: 8 }} />
                </div>
                <div style={{
                  padding: '0.85rem', border: '1px dashed var(--border-default)', borderRadius: 8, background: 'var(--bg-elevated)',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem'
                }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {attachedFileName ? `Attached Web HTML: ${attachedFileName}` : 'Attach Webpage HTML Source / Screenshot (.html, .png)'}
                  </span>
                  <label className="btn-secondary" style={{ cursor: 'pointer', margin: 0, fontSize: '0.72rem', borderRadius: 6 }}>
                    Attach File
                    <input type="file" accept=".html,.htm,image/*" onChange={handleFileUpload} style={{ display: 'none' }} />
                  </label>
                </div>
              </div>
            )}

            {/* Textarea */}
            <div>
              <label className="section-label" htmlFor="scam-text">{channel} Content / Message Transcript</label>
              <textarea
                id="scam-text"
                className="input-field"
                value={text}
                onChange={e => setText(e.target.value)}
                rows={5}
                placeholder={`Enter suspicious ${channel.toLowerCase()} content to analyze...`}
                style={{ resize: 'vertical', fontFamily: 'inherit', borderRadius: 10, fontWeight: 400 }}
              />
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
              <button
                className="btn-primary"
                disabled={busy || streaming || !text.trim()}
                style={{ minHeight: 38, borderRadius: 8, fontWeight: 400 }}
              >
                {busy ? <span className="spinner" /> : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                )}
                {busy ? 'Analyzing...' : `Analyze ${channel} Content`}
              </button>

              {channel === 'Voice' && (
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={busy || streaming}
                  onClick={() => void runCallStreamSimulation()}
                  style={{ minHeight: 38, borderRadius: 8, fontWeight: 400 }}
                >
                  {streaming ? <span className="spinner" /> : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
                  )}
                  Stream Call Chunks
                </button>
              )}
            </div>
          </form>

          {error && (
            <div style={{
              marginTop: '1rem',
              padding: '0.75rem 1rem',
              background: 'var(--bg-elevated)',
              border: '1px solid #f43f5e',
              borderRadius: 8,
              color: '#f43f5e',
              fontSize: '0.85rem',
              fontWeight: 400,
            }}>
              Error: {error}
            </div>
          )}
        </div>

        {/* Right Column: Interactive Intelligence Output Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {/* Live Stream Simulator Output (Voice channel) */}
          {channel === 'Voice' && streamChunks.length > 0 && (
            <div className="glass-card animate-fade-in" style={{ padding: '1.25rem', borderRadius: 10 }}>
              <p className="section-label" style={{ marginBottom: '0.65rem' }}>Real-Time Stream Chunks Feed</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                {streamChunks.map(c => (
                  <div key={c.seq} style={{
                    padding: '0.65rem 0.85rem', borderRadius: 8,
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap'
                  }}>
                    <div style={{ flex: 1 }}>
                      <span style={{ fontSize: '0.7rem', fontWeight: 400, color: 'var(--text-muted)', display: 'block' }}>
                        Chunk #{c.seq}
                      </span>
                      <span style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', fontWeight: 400 }}>"{c.text}"</span>
                    </div>
                    {c.res && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                        <span style={{ fontSize: '0.82rem', fontWeight: 400, color: c.res.risk_score >= 0.5 ? '#f43f5e' : '#10b981' }}>
                          {Math.round(c.res.risk_score * 100)}%
                        </span>
                        <RiskBadge level={c.res.risk_level} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Single Analysis Result */}
          {result ? (
            <div className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                  <CircularProgress value={result.risk_score} />
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.6rem' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>Evaluated Risk</span>
                      <RiskBadge level={result.risk_level} />
                      {result.alerted && (
                        <span style={{ padding: '0.15rem 0.45rem', background: 'rgba(244,63,94,0.12)', border: '1px solid #f43f5e', borderRadius: 6, fontSize: '0.68rem', color: '#f43f5e', fontWeight: 400 }}>
                          Alert Dispatched
                        </span>
                      )}
                    </div>
                    <p style={{ margin: '0 0 0.85rem', fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, fontWeight: 400 }}>
                      {result.explanation || result.recommend_action}
                    </p>
                    {result.recommend_action && (
                      <div style={{ padding: '0.6rem 0.85rem', background: 'var(--bg-elevated)', borderRadius: 8, borderLeft: '3px solid var(--text-primary)', fontSize: '0.8rem', color: 'var(--text-primary)', marginBottom: '0.5rem', fontWeight: 400 }}>
                        Action Advice: {result.recommend_action}
                      </div>
                    )}
                    {result.request_id && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                        Model: {result.model_version} · Audit ID: {result.request_id.slice(0, 8)}...
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Signals */}
              {((result.signals && result.signals.length > 0) || (result.matched_signals && result.matched_signals.length > 0)) && (
                <div className="glass-card" style={{ padding: '1.15rem', borderRadius: 10 }}>
                  <p className="section-label">Matched Scam Signals</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                    {(result.signals || result.matched_signals || []).map((s, i) => (
                      <span key={i} className="tag">{s}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Raw JSON Payload */}
              <JsonViewer data={result} title="Raw API Response Payload" defaultOpen={false} />
            </div>
          ) : (
            <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Live Neural Threat Signal Monitor
                  </h3>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    Active threat indicators scanned by backend AI model
                  </span>
                </div>
                <span className="tag" style={{ fontSize: '0.7rem' }}>Ready for input</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 8 }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.2rem', fontWeight: 400 }}>Impersonation Signals</div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>CBI, Police, Customs & Bank KYC</div>
                </div>
                <div style={{ padding: '0.75rem', background: 'var(--bg-elevated)', borderRadius: 8 }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.2rem', fontWeight: 400 }}>Urgency / Coercion</div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>Digital Arrest & Immediate Payment</div>
                </div>
              </div>

              <div style={{ padding: '0.85rem 1rem', background: 'var(--bg-elevated)', borderRadius: 8, borderLeft: '3px solid #10b981', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <span style={{ fontSize: '0.8rem', fontWeight: 400, color: 'var(--text-primary)', display: 'block' }}>
                    Quick Launch Threat Check
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    Click "Analyze {channel} Content" on the left to run immediate AI evaluation
                  </span>
                </div>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={(e) => void handleSubmit(e as unknown as FormEvent)}
                  style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem', borderRadius: 6 }}
                >
                  Evaluate Now
                </button>
              </div>
            </div>
          )}
        </div>

      </div>

    </div>
  )
}

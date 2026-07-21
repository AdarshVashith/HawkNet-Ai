import { useState, type FormEvent } from 'react'
import {
  submitCitizenReport,
  assessCitizenRisk,
  postBotWebhook,
  type CitizenAssessResult,
  type BotWebhookResult,
} from '../lib/api'
import RiskBadge from '../components/RiskBadge'
import JsonViewer from '../components/JsonViewer'

type ReportResult = {
  report_id: string
  status: string
  message: string
}

// ── English & Hindi Translations ──────────────────────────────────
const CONTENT = {
  en: {
    headerTitle: 'Citizen Shield Intake & Threat Assessment Portal',
    headerBadge: 'Anonymous Intake',
    subTitle: 'Operated in accordance with Ministry of Home Affairs (MHA) & I4C Public Safety Guidelines.',
    govTrustBadge: 'MHA / I4C Cyber Crime Integration',
    presetsLabel: 'Featured Threat Scenarios (Click to Test)',
    categoryLabel: 'Incident Category',
    descLabel: 'Description of Suspicious Situation / Threat',
    descPlaceholder: 'Describe what happened. Mention if someone claimed to be police/CBI, asked for money, or demanded you stay on video call...',
    indicatorsTitle: 'Threat Assessment Indicators',
    checkVideo: 'Did caller order you to stay on video call (Digital Arrest)?',
    checkAuthority: 'Was an authority mentioned (CBI, Police, Customs, ED, RBI)?',
    checkPayment: 'Was urgent payment, UPI transfer, or OTP demanded?',
    locationLabel: 'Incident Location / City (optional)',
    locationPlaceholder: 'e.g. Connaught Place, New Delhi',
    anonLabel: 'Submit anonymously',
    anonDesc: '(identity hidden from database)',
    submitBtn: 'Submit Official Report',
    assessBtn: 'Assess Risk Only',
    submitting: 'Submitting & Assessing...',
    receiptTitle: 'Official Receipt Generated',
    helplineTitle: 'National Cyber Crime Emergency Helpline:',
    helplineAction: 'Dial 1930 (Immediate Bank Freeze)',
    stepsTitle: 'Immediate Safety Protocol Steps',
    triageTitle: 'Citizen Intake Triage Monitor',
    triageSub: 'Real-time threat assessment rules & 1930 Helpline dispatch',
    categories: [
      { value: 'digital_arrest', label: 'Digital Arrest / Extortion Call' },
      { value: 'scam', label: 'Online Scam / Phishing' },
      { value: 'counterfeit', label: 'Counterfeit Product / Seller' },
      { value: 'harassment', label: 'Cyberbullying / Blackmail' },
      { value: 'other', label: 'Other Public Safety Threat' },
    ],
    presets: [
      {
        name: 'Digital Arrest Threat Call',
        category: 'digital_arrest',
        riskTag: 'CRITICAL THREAT',
        tagColor: '#f43f5e',
        desc: 'CBI officer called saying my Aadhaar is linked to drug trafficking. Demanding I stay on video call for digital arrest inspection.',
        qa: { video_hold: true, authority_mentioned: 'CBI', payment_requested: true },
      },
      {
        name: 'Bank OTP Phishing SMS',
        category: 'scam',
        riskTag: 'HIGH RISK PHISHING',
        tagColor: '#f97316',
        desc: 'Received URGENT SMS saying my bank account is suspended. Link asks for Netbanking password and OTP to unlock.',
        qa: { authority_mentioned: 'HDFC Bank', payment_requested: false },
      },
      {
        name: 'Part-Time Youtube Like Scam',
        category: 'scam',
        riskTag: 'SUSPICIOUS JOB',
        tagColor: '#f59e0b',
        desc: 'WhatsApp message offering 5000 INR per day for liking YouTube videos. Asking for 2000 INR deposit to unlock VIP tasks.',
        qa: { payment_requested: true },
      },
      {
        name: 'Fake Counterfeit Medicine',
        category: 'counterfeit',
        riskTag: 'HEALTH RISK',
        tagColor: '#f43f5e',
        desc: 'Unverified online pharmacy selling prescription medicine with missing hologram security seal and altered batch numbers.',
        qa: {},
      },
    ],
  },
  hi: {
    headerTitle: 'सिटिजन शील्ड - नागरिक सुरक्षा एवं शिकायत पोर्टल',
    headerBadge: 'गोपनीय शिकायत',
    subTitle: 'गृह मंत्रालय (MHA) और I4C (भारतीय साइबर अपराध समन्वय केंद्र) के सार्वजनिक सुरक्षा दिशानिर्देशों के तहत संचालित।',
    govTrustBadge: 'गृह मंत्रालय (MHA) व I4C पोर्टल से संबद्ध',
    presetsLabel: 'प्रमुख साइबर अपराध उदाहरण (परीक्षण के लिए क्लिक करें)',
    categoryLabel: 'घटना की श्रेणी चुनिए',
    descLabel: 'संदेहास्पद स्थिति या खतरे का विवरण',
    descPlaceholder: 'क्या हुआ इसका पूरा विवरण लिखें। यदि किसी ने पुलिस/CBI अधिकारी बनकर पैसे या वीडियो कॉल पर रहने (डिजिटल अरेस्ट) का दबाव बनाया तो लिखें...',
    indicatorsTitle: 'खतरे का आकलन करने वाले मुख्य संकेतक',
    checkVideo: 'क्या कॉल करने वाले ने आपको वीडियो कॉल पर रहने (डिजिटल अरेस्ट) का आदेश दिया?',
    checkAuthority: 'क्या किसी सरकारी एजेंसी (CBI, पुलिस, कस्टम, ED, RBI) का नाम लिया गया?',
    checkPayment: 'क्या तुरंत पैसे भेजने, UPI ट्रांसफर करने या OTP साझा करने का दबाव बनाया गया?',
    locationLabel: 'घटना का स्थान / शहर (वैल्पिक)',
    locationPlaceholder: 'उदा. कनाट प्लेस, नई दिल्ली',
    anonLabel: 'गुप्त रूप से रिपोर्ट करें',
    anonDesc: '(आपकी पहचान डेटाबेस से छिपी रहेगी)',
    submitBtn: 'आधिकारिक रिपोर्ट जमा करें',
    assessBtn: 'केवल जोखिम का आकलन करें',
    submitting: 'आकलन किया जा रहा है...',
    receiptTitle: 'आधिकारिक शिकायत रसीद उत्पन्न',
    helplineTitle: 'राष्ट्रीय साइबर अपराध आपातकालीन हेल्पलाइन:',
    helplineAction: '1930 पर कॉल करें (बैंक खाता तुरंत फ्रीज करें)',
    stepsTitle: 'तत्काल सुरक्षा निर्देश कदम',
    triageTitle: 'नागरिक शिकायत प्राथमिक आकलन मॉनिटर',
    triageSub: 'वास्तविक समय जोखिम नियम एवं 1930 हेल्पलाइन हेल्प डेस्क',
    categories: [
      { value: 'digital_arrest', label: 'डिजिटल अरेस्ट / जबरन वसूली कॉल' },
      { value: 'scam', label: 'ऑनलाइन धोखाधड़ी / फ़िशिंग' },
      { value: 'counterfeit', label: 'नक़ली सामान / विक्रेता' },
      { value: 'harassment', label: 'साइबर धमकी / ब्लैकमेल' },
      { value: 'other', label: 'अन्य नागरिक सुरक्षा खतरा' },
    ],
    presets: [
      {
        name: 'डिजिटल अरेस्ट साइबर कॉल',
        category: 'digital_arrest',
        riskTag: 'गंभीर खतरा',
        tagColor: '#f43f5e',
        desc: 'CBI अधिकारी बताकर फोन आया कि मेरा आधार कार्ड ड्रग तस्करी से जुड़ा है। डिजिटल अरेस्ट की जांच के लिए वीडियो कॉल पर बने रहने का दबाव बना रहे हैं।',
        qa: { video_hold: true, authority_mentioned: 'CBI', payment_requested: true },
      },
      {
        name: 'बैंक OTP फ़िशिंग एसएमएस',
        category: 'scam',
        riskTag: 'उच्च जोखिम फ़िशिंग',
        tagColor: '#f97316',
        desc: 'अति आवश्यक SMS मिला कि बैंक खाता ब्लॉक कर दिया गया है। लिंक खोलने पर नेटबैंकिंग पासवर्ड और OTP मांगा जा रहा है।',
        qa: { authority_mentioned: 'HDFC बैंक', payment_requested: false },
      },
      {
        name: 'यूट्यूब लाइक पार्ट-टाइम जॉब ठगी',
        category: 'scam',
        riskTag: 'संदेहास्पद जॉब',
        tagColor: '#f59e0b',
        desc: 'व्हाट्सएप संदेश मिला कि यूट्यूब वीडियो लाइक करके 5000 रु रोजाना कमाएं। वीआईपी टास्क अनलॉक करने के लिए 2000 रु जमा करने को कहा गया है।',
        qa: { payment_requested: true },
      },
      {
        name: 'नकली दवा विक्रेता फ़्रॉड',
        category: 'counterfeit',
        riskTag: 'स्वास्थ्य जोखिम',
        tagColor: '#f43f5e',
        desc: 'अज्ञात ऑनलाइन फ़ार्मेसी से खरीदी गई दवा में सुरक्षा होलोग्राम सील गायब है और बैच नंबर बदला हुआ लगता है।',
        qa: {},
      },
    ],
  },
}

export default function CitizenShield() {
  const [activeTab, setActiveTab] = useState<'portal' | 'bot'>('portal')
  const [lang, setLang] = useState<'en' | 'hi'>('en')
  const t = CONTENT[lang]

  // Portal state
  const [category, setCategory] = useState('digital_arrest')
  const [description, setDescription] = useState('')
  const [location, setLocation] = useState('')
  const [anonymous, setAnonymous] = useState(true)

  const [checkVideoHold, setCheckVideoHold] = useState(false)
  const [checkAuthority, setCheckAuthority] = useState('')
  const [checkPayment, setCheckPayment] = useState(false)

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [reportResult, setReportResult] = useState<ReportResult | null>(null)
  const [assessResult, setAssessResult] = useState<CitizenAssessResult | null>(null)

  // WhatsApp Bot state
  const [botPlatform, setBotPlatform] = useState<'whatsapp' | 'telegram'>('whatsapp')
  const [botMessage, setBotMessage] = useState('Forwarded message: URGENT SBI account frozen due to KYC expiry. Click bit.ly/sbi-verify to unlock immediately.')
  const [botSender, setBotSender] = useState('+919876543210')
  const [botBusy, setBotBusy] = useState(false)
  const [botResult, setBotResult] = useState<BotWebhookResult | null>(null)

  function applyPreset(p: typeof CONTENT.en.presets[0]) {
    setCategory(p.category)
    setDescription(p.desc)
    setCheckVideoHold(!!p.qa.video_hold)
    setCheckAuthority(p.qa.authority_mentioned || '')
    setCheckPayment(!!p.qa.payment_requested)
    setReportResult(null)
    setAssessResult(null)
  }

  async function handlePortalSubmit(e: FormEvent, assessOnly = false) {
    e.preventDefault()
    setBusy(true); setError(null); setReportResult(null); setAssessResult(null)

    const qaAnswers: Record<string, string | boolean> = {}
    if (checkVideoHold) qaAnswers.video_hold = true
    if (checkAuthority.trim()) qaAnswers.authority_mentioned = checkAuthority.trim()
    if (checkPayment) qaAnswers.payment_requested = true

    try {
      const assessData = await assessCitizenRisk(description, qaAnswers, lang)
      setAssessResult(assessData)

      if (!assessOnly) {
        const reportData = await submitCitizenReport(category, description, location || undefined, anonymous)
        setReportResult(reportData)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed')
    } finally {
      setBusy(false)
    }
  }

  async function handleBotSubmit(e: FormEvent) {
    e.preventDefault()
    setBotBusy(true); setBotResult(null)
    try {
      const res = await postBotWebhook(botMessage, botPlatform, lang, botSender)
      setBotResult(res)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Bot webhook error')
    } finally {
      setBotBusy(false)
    }
  }

  return (
    <div className="animate-fade-in" style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      
      {/* Top Bar with Hindi Toggle & Tab Navigation */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.85rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              {t.headerTitle}
            </h2>
            <RiskBadge level="low" label={t.headerBadge} />
          </div>
          <p style={{ margin: '0.2rem 0 0', color: 'var(--text-secondary)', fontSize: '0.8125rem', fontWeight: 400 }}>
            {t.subTitle}
          </p>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          {/* Tabs */}
          <div style={{ display: 'flex', background: 'var(--bg-elevated)', borderRadius: 8, padding: 3, border: '1px solid var(--border-subtle)' }}>
            <button
              type="button"
              onClick={() => setActiveTab('portal')}
              style={{
                padding: '0.3rem 0.75rem', fontSize: '0.78rem', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: activeTab === 'portal' ? 'var(--card-bg)' : 'transparent',
                color: activeTab === 'portal' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'portal' ? 700 : 400,
              }}
            >
              Intake Portal
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('bot')}
              style={{
                padding: '0.3rem 0.75rem', fontSize: '0.78rem', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: activeTab === 'bot' ? '#10b981' : 'transparent',
                color: activeTab === 'bot' ? '#ffffff' : 'var(--text-secondary)',
                fontWeight: activeTab === 'bot' ? 700 : 400,
              }}
            >
              WhatsApp & Telegram Bot
            </button>
          </div>

          {/* Language Selector */}
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setLang(l => l === 'en' ? 'hi' : 'en')}
            style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem', borderRadius: 8, fontWeight: 700 }}
          >
            {lang === 'en' ? 'हिंदी' : 'English'}
          </button>
        </div>
      </div>

      {/* ── TAB 1: INTAKE PORTAL ─────────────────────────────────────── */}
      {activeTab === 'portal' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          {/* Government Trust Banner */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem',
            padding: '0.75rem 1.1rem', background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: 10,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block' }}>
                  {t.govTrustBadge}
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                  Cross-checks Sanchar Saathi DoT Blacklist · Sec 65B Indian Evidence Act Certified
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ padding: '0.2rem 0.6rem', borderRadius: 6, background: '#10b98122', color: '#10b981', border: '1px solid #10b981', fontSize: '0.72rem', fontWeight: 700 }}>
                1930 Helpline Online
              </span>
            </div>
          </div>

          {/* Featured Presets */}
          <div>
            <p className="section-label" style={{ marginBottom: '0.45rem' }}>{t.presetsLabel}</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
              {t.presets.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="glass-card"
                  onClick={() => applyPreset(p)}
                  style={{
                    padding: '0.85rem 1rem', borderRadius: 10, cursor: 'pointer', textAlign: 'left',
                    display: 'flex', flexDirection: 'column', gap: '0.35rem', background: 'var(--card-bg)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>{p.name}</span>
                    <span style={{ fontSize: '0.62rem', fontWeight: 700, color: p.tagColor, padding: '0.1rem 0.4rem', background: 'var(--bg-elevated)', borderRadius: 6, border: `1px solid ${p.tagColor}` }}>
                      {p.riskTag}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 400 }}>{p.desc.slice(0, 75)}...</div>
                </button>
              ))}
            </div>
          </div>

          {/* Form + Results Layout */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '1.25rem', alignItems: 'flex-start' }}>
            
            {/* Form Column */}
            <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
              <form onSubmit={(e) => void handlePortalSubmit(e, false)} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
                <div>
                  <label className="section-label" htmlFor="cs-cat">{t.categoryLabel}</label>
                  <select id="cs-cat" className="input-field" value={category} onChange={e => setCategory(e.target.value)} style={{ borderRadius: 8 }}>
                    {t.categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>

                <div>
                  <label className="section-label" htmlFor="cs-desc">{t.descLabel}</label>
                  <textarea
                    id="cs-desc" className="input-field" rows={4} value={description}
                    onChange={e => setDescription(e.target.value)} placeholder={t.descPlaceholder}
                    style={{ borderRadius: 8 }} required
                  />
                </div>

                {/* Threat Indicators Checklist */}
                <div style={{ padding: '0.85rem', background: 'var(--bg-elevated)', borderRadius: 8, border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)' }}>{t.indicatorsTitle}</span>
                  
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', fontSize: '0.78rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <input type="checkbox" checked={checkVideoHold} onChange={e => setCheckVideoHold(e.target.checked)} />
                    {t.checkVideo}
                  </label>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{t.checkAuthority}</span>
                    <input
                      className="input-field" placeholder="e.g. CBI, Police" value={checkAuthority}
                      onChange={e => setCheckAuthority(e.target.value)}
                      style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', width: 140, borderRadius: 6 }}
                    />
                  </div>

                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', fontSize: '0.78rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <input type="checkbox" checked={checkPayment} onChange={e => setCheckPayment(e.target.checked)} />
                    {t.checkPayment}
                  </label>
                </div>

                <div>
                  <label className="section-label" htmlFor="cs-loc">{t.locationLabel}</label>
                  <input
                    id="cs-loc" className="input-field" value={location} onChange={e => setLocation(e.target.value)}
                    placeholder={t.locationPlaceholder} style={{ borderRadius: 8 }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <input id="cs-anon" type="checkbox" checked={anonymous} onChange={e => setAnonymous(e.target.checked)} />
                  <label htmlFor="cs-anon" style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <strong>{t.anonLabel}</strong> <span style={{ color: 'var(--text-muted)' }}>{t.anonDesc}</span>
                  </label>
                </div>

                <div style={{ display: 'flex', gap: '0.6rem' }}>
                  <button className="btn-primary" disabled={busy || !description.trim()} style={{ flex: 1, borderRadius: 8, fontWeight: 400, minHeight: 38 }}>
                    {busy ? <span className="spinner" /> : t.submitBtn}
                  </button>
                  <button type="button" className="btn-secondary" disabled={busy || !description.trim()} onClick={(e) => void handlePortalSubmit(e, true)} style={{ borderRadius: 8, fontWeight: 400 }}>
                    {t.assessBtn}
                  </button>
                </div>
              </form>

              {error && (
                <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: 'var(--bg-elevated)', border: '1px solid #f43f5e', borderRadius: 8, color: '#f43f5e', fontSize: '0.85rem' }}>
                  Error: {error}
                </div>
              )}
            </div>

            {/* Results Column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {assessResult ? (
                <div className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  
                  {/* Verdict Banner */}
                  <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10, border: `1px solid ${assessResult.verdict.includes('high') ? '#f43f5e' : '#10b981'}` }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
                      <RiskBadge level={assessResult.verdict.includes('high') ? 'critical' : assessResult.verdict.includes('suspicious') ? 'high' : 'low'} label={assessResult.verdict.replace(/_/g, ' ').toUpperCase()} />
                      <span style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {Math.round(assessResult.confidence_score * 100)}% Confidence
                      </span>
                    </div>

                    <p style={{ margin: '0 0 1rem', fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                      {assessResult.plain_explanation}
                    </p>

                    {/* 1930 Helpline Dispatch Button */}
                    <div style={{ padding: '0.85rem', background: '#f43f5e15', border: '1px solid #f43f5e', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div>
                        <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f43f5e', display: 'block' }}>{t.helplineTitle}</span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Freezes suspicious transactions across all Indian banks</span>
                      </div>
                      <a href={`tel:${assessResult.helpline}`} style={{ padding: '0.35rem 0.85rem', background: '#f43f5e', color: '#ffffff', borderRadius: 6, fontWeight: 700, fontSize: '0.78rem', textDecoration: 'none' }}>
                        {t.helplineAction}
                      </a>
                    </div>
                  </div>

                  {reportResult && (
                    <div style={{ padding: '1rem', background: 'var(--bg-elevated)', border: '1px solid #10b981', borderRadius: 8, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                      <strong>{t.receiptTitle}:</strong> <code style={{ fontFamily: 'monospace' }}>{reportResult.report_id}</code>
                    </div>
                  )}

                  <JsonViewer data={{ assessResult, reportResult }} title="Technical Audit Payload" defaultOpen={false} />

                </div>
              ) : (
                <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
                  <span className="section-label">{t.triageTitle}</span>
                  <p style={{ margin: '0.3rem 0 0', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{t.triageSub}</p>
                </div>
              )}
            </div>

          </div>

        </div>
      )}

      {/* ── TAB 2: WHATSAPP & TELEGRAM BOT SIMULATOR ─────────────────── */}
      {activeTab === 'bot' && (
        <div className="animate-slide-up" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '1.25rem', alignItems: 'flex-start' }}>
          
          {/* Simulator Form */}
          <div className="glass-card" style={{ padding: '1.4rem', borderRadius: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  WhatsApp & Telegram Bot Webhook Simulator
                </h3>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Simulates instant 24/7 citizen chat safety checks without app installation
                </span>
              </div>
            </div>

            <form onSubmit={handleBotSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label className="section-label" htmlFor="bot-platform">Messaging Platform</label>
                <select id="bot-platform" className="input-field" value={botPlatform} onChange={e => setBotPlatform(e.target.value as 'whatsapp' | 'telegram')} style={{ borderRadius: 8 }}>
                  <option value="whatsapp">WhatsApp Business API Webhook</option>
                  <option value="telegram">Telegram Bot Webhook</option>
                </select>
              </div>

              <div>
                <label className="section-label" htmlFor="bot-sender">Sender Phone / Handle</label>
                <input id="bot-sender" className="input-field" value={botSender} onChange={e => setBotSender(e.target.value)} style={{ borderRadius: 8 }} />
              </div>

              <div>
                <label className="section-label" htmlFor="bot-msg">Forwarded Chat Message to Check</label>
                <textarea id="bot-msg" className="input-field" rows={4} value={botMessage} onChange={e => setBotMessage(e.target.value)} style={{ borderRadius: 8 }} required />
              </div>

              {/* Quick Presets */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                <button type="button" className="btn-secondary" onClick={() => setBotMessage('URGENT SBI account frozen. Click bit.ly/sbi-verify now')} style={{ fontSize: '0.72rem', borderRadius: 6 }}>
                  SBI KYC Phishing
                </button>
                <button type="button" className="btn-secondary" onClick={() => setBotMessage('CBI डिजिटल अरेस्ट वारंट जारी हुआ है। तुरंत 50,000 रुपये जमा करें वरना पुलिस आएगी।')} style={{ fontSize: '0.72rem', borderRadius: 6 }}>
                  CBI डिजिटल अरेस्ट (Hindi)
                </button>
              </div>

              <button className="btn-primary" disabled={botBusy || !botMessage.trim()} style={{ background: '#10b981', color: '#ffffff', borderRadius: 8, fontWeight: 400, minHeight: 38 }}>
                {botBusy ? <span className="spinner" /> : 'Send Forwarded Message to Bot Webhook'}
              </button>
            </form>
          </div>

          {/* Live Chat Bubble Interface */}
          <div className="glass-card" style={{ padding: 0, borderRadius: 10, background: '#0b141a', border: '1px solid var(--border-subtle)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            
            {/* WhatsApp Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.6rem 1rem', background: '#202c33' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                {/* Profile Pic Placeholder */}
                <div style={{ width: 40, height: 40, borderRadius: '50%', background: '#111b21', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #2a3942' }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8696a0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                  </svg>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '1rem', fontWeight: 500, color: '#e9edef', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    Citizen Shield {botPlatform === 'whatsapp' ? 'WA' : 'TG'}
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="#00a884">
                      <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm-1.9 14.7L5.7 12.3l1.4-1.4 3 3 7.9-7.9 1.4 1.4-9.3 9.3z" />
                    </svg>
                  </span>
                  <span style={{ fontSize: '0.8rem', color: '#8696a0' }}>+91 1930 • Official Govt Helpline</span>
                </div>
              </div>
            </div>

            {/* Chat Body */}
            <div style={{ 
              display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem 4%', minHeight: 320, 
              background: '#0b141a', backgroundImage: 'radial-gradient(#202c33 1px, transparent 1px)', backgroundSize: '20px 20px', backgroundPosition: '0 0, 10px 10px'
            }}>
              
              {/* Encryption Banner */}
              <div style={{ alignSelf: 'center', background: '#ffeecd', color: '#543b16', padding: '0.3rem 0.6rem', borderRadius: 8, fontSize: '0.75rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 500 }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                Messages are end-to-end encrypted.
              </div>

              {/* User Message Bubble */}
              <div style={{ position: 'relative', alignSelf: 'flex-end', maxWidth: '75%', background: '#005c4b', color: '#e9edef', padding: '0.4rem 0.5rem 1.2rem 0.5rem', borderRadius: '7.5px', borderTopRightRadius: '0px', fontSize: '0.9rem', lineHeight: 1.4, boxShadow: '0 1px 0.5px rgba(11,20,26,.13)' }}>
                {botMessage}
                <span style={{ position: 'absolute', bottom: '0.2rem', right: '0.4rem', fontSize: '0.65rem', color: 'rgba(255,255,255,0.6)' }}>
                  {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ✓✓
                </span>
                {/* Tail */}
                <div style={{ position: 'absolute', top: 0, right: '-8px', width: 8, height: 13 }}>
                  <svg viewBox="0 0 8 13" width="8" height="13" style={{ fill: '#005c4b' }}>
                    <path d="M5.188 1H0v11.193l6.467-8.625C7.526 2.156 6.958 1 5.188 1z" />
                  </svg>
                </div>
              </div>

              {/* Bot Reply Bubble */}
              {botBusy ? (
                <div style={{ alignSelf: 'flex-start', background: '#202c33', color: '#8696a0', padding: '0.5rem 0.75rem', borderRadius: '7.5px', borderTopLeftRadius: '0px', fontSize: '0.9rem', fontStyle: 'italic', boxShadow: '0 1px 0.5px rgba(11,20,26,.13)' }}>
                  typing...
                </div>
              ) : botResult ? (
                <div style={{ position: 'relative', alignSelf: 'flex-start', maxWidth: '85%', background: '#202c33', color: '#e9edef', padding: '0.4rem 0.5rem 1.2rem 0.5rem', borderRadius: '7.5px', borderTopLeftRadius: '0px', fontSize: '0.9rem', whiteSpace: 'pre-wrap', lineHeight: 1.4, boxShadow: '0 1px 0.5px rgba(11,20,26,.13)' }}>
                  {botResult.reply_text}
                  <span style={{ position: 'absolute', bottom: '0.2rem', right: '0.4rem', fontSize: '0.65rem', color: '#8696a0' }}>
                    {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  {/* Tail */}
                  <div style={{ position: 'absolute', top: 0, left: '-8px', width: 8, height: 13 }}>
                    <svg viewBox="0 0 8 13" width="8" height="13" style={{ fill: '#202c33' }}>
                      <path d="M2.812 1H8v11.193L1.533 3.568C.474 2.156 1.042 1 2.812 1z" />
                    </svg>
                  </div>
                </div>
              ) : (
                <div style={{ alignSelf: 'flex-start', background: '#202c33', color: '#8696a0', padding: '0.6rem 0.75rem', borderRadius: '7.5px', borderTopLeftRadius: '0px', fontSize: '0.85rem', boxShadow: '0 1px 0.5px rgba(11,20,26,.13)' }}>
                  Welcome to the official Citizen Shield bot. Forward any suspicious message to check for scams instantly.
                  {/* Tail */}
                  <div style={{ position: 'absolute', top: 0, left: '-8px', width: 8, height: 13 }}>
                    <svg viewBox="0 0 8 13" width="8" height="13" style={{ fill: '#202c33' }}>
                      <path d="M2.812 1H8v11.193L1.533 3.568C.474 2.156 1.042 1 2.812 1z" />
                    </svg>
                  </div>
                </div>
              )}

            </div>
          </div>

        </div>
      )}

    </div>
  )
}

import { useState } from 'react'

interface JsonViewerProps {
  data: unknown
  title?: string
  defaultOpen?: boolean
}

type TokenType = 'key' | 'string' | 'number' | 'boolean' | 'null' | 'punctuation'

interface Token {
  type: TokenType
  value: string
}

function tokenize(json: string): Token[] {
  const tokens: Token[] = []
  let i = 0

  while (i < json.length) {
    const ch = json[i]

    if (/\s/.test(ch)) {
      tokens.push({ type: 'punctuation', value: ch })
      i++
      continue
    }

    if (ch === '"') {
      let str = '"'
      i++
      while (i < json.length && json[i] !== '"') {
        if (json[i] === '\\') { str += json[i++]; }
        str += json[i++]
      }
      str += '"'
      i++
      let j = i
      while (j < json.length && /\s/.test(json[j])) j++
      if (json[j] === ':') {
        tokens.push({ type: 'key', value: str })
      } else {
        tokens.push({ type: 'string', value: str })
      }
      continue
    }

    if (/[-\d]/.test(ch)) {
      let num = ''
      while (i < json.length && /[-\d.eE+]/.test(json[i])) { num += json[i++] }
      tokens.push({ type: 'number', value: num })
      continue
    }

    if (json.startsWith('true', i))  { tokens.push({ type: 'boolean', value: 'true' });  i += 4; continue }
    if (json.startsWith('false', i)) { tokens.push({ type: 'boolean', value: 'false' }); i += 5; continue }
    if (json.startsWith('null', i))  { tokens.push({ type: 'null',    value: 'null' });  i += 4; continue }

    tokens.push({ type: 'punctuation', value: ch })
    i++
  }

  return tokens
}

const MONOCHROME_TOKEN_COLORS: Record<TokenType, string> = {
  key:         'var(--text-primary)',
  string:      'var(--text-secondary)',
  number:      '#10b981',
  boolean:     '#f59e0b',
  null:        'var(--text-muted)',
  punctuation: 'var(--text-muted)',
}

function HighlightedJson({ json }: { json: string }) {
  const tokens = tokenize(json)
  return (
    <code style={{ display: 'block', fontWeight: 400 }}>
      {tokens.map((tok, idx) => (
        <span key={idx} style={{ color: MONOCHROME_TOKEN_COLORS[tok.type], fontWeight: 400 }}>{tok.value}</span>
      ))}
    </code>
  )
}

function IconSettingsGear() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  )
}

function IconChevronDown() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  )
}

export default function JsonViewer({ data, title, defaultOpen = false }: JsonViewerProps) {
  const [open, setOpen] = useState(defaultOpen)
  const json = JSON.stringify(data, null, 2)

  return (
    <div style={{
      border: '1px solid var(--border-subtle)',
      borderRadius: 10,
      overflow: 'hidden',
      background: 'var(--card-bg)',
      transition: 'all 0.15s ease',
    }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.6rem 0.85rem',
          background: 'var(--bg-elevated)',
          border: 'none',
          borderBottom: open ? '1px solid var(--border-subtle)' : 'none',
          cursor: 'pointer',
          color: 'var(--text-primary)',
          gap: '0.5rem',
          fontWeight: 400,
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem', fontWeight: 400 }}>
          <IconSettingsGear />
          {title ?? 'Payload & Technical Config'}
        </span>
        <span style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.3rem',
          fontSize: '0.72rem',
          color: 'var(--text-muted)',
          fontWeight: 400,
          transform: open ? 'rotate(180deg)' : 'none',
          transition: 'transform 0.2s ease',
        }}>
          <IconChevronDown />
        </span>
      </button>

      {open && (
        <div style={{ overflowX: 'auto', maxHeight: 380, overflowY: 'auto', background: 'var(--bg-elevated)', padding: '0.85rem' }}>
          <pre style={{
            margin: 0,
            fontSize: '0.75rem',
            lineHeight: 1.65,
            fontWeight: 400,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          }}>
            <HighlightedJson json={json} />
          </pre>
        </div>
      )}
    </div>
  )
}

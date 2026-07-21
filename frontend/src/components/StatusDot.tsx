interface StatusDotProps {
  status: 'ok' | 'error' | 'loading'
  label?: string
}

const MONOCHROME_STATUS = {
  ok:      { color: '#ffffff' },
  error:   { color: '#888888' },
  loading: { color: '#aaaaaa' },
}

export default function StatusDot({ status, label }: StatusDotProps) {
  const s = MONOCHROME_STATUS[status] ?? MONOCHROME_STATUS.ok

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}>
      <span style={{ position: 'relative', display: 'inline-flex', width: 8, height: 8 }}>
        <span style={{
          position: 'relative',
          width: 8, height: 8,
          borderRadius: '50%',
          background: s.color,
        }} />
      </span>
      {label && (
        <span style={{ fontSize: '0.78rem', fontWeight: 400, color: 'var(--text-secondary)' }}>
          {label}
        </span>
      )}
    </span>
  )
}

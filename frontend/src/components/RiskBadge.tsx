interface RiskBadgeProps {
  level: 'low' | 'medium' | 'high' | 'critical' | string
  label?: string
}

const STAT_RISK_STYLES: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  low:      { bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.35)', text: '#10b981', dot: '#10b981' },
  medium:   { bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.35)', text: '#f59e0b', dot: '#f59e0b' },
  high:     { bg: 'rgba(249, 115, 22, 0.12)', border: 'rgba(249, 115, 22, 0.35)', text: '#f97316', dot: '#f97316' },
  critical: { bg: 'rgba(244, 63, 94, 0.15)',  border: 'rgba(244, 63, 94, 0.40)',  text: '#f43f5e', dot: '#f43f5e' },
}

const RISK_LABELS: Record<string, string> = {
  low: 'Low Risk',
  medium: 'Medium Risk',
  high: 'High Risk',
  critical: 'Critical Risk',
}

export default function RiskBadge({ level, label }: RiskBadgeProps) {
  const normalized = level?.toLowerCase() ?? 'unknown'
  const style = STAT_RISK_STYLES[normalized] ?? {
    bg: '#121212',
    border: '#333333',
    text: '#ffffff',
    dot: '#888888',
  }
  const displayLabel = label ?? RISK_LABELS[normalized] ?? level

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: '0.2rem 0.6rem',
        background: style.bg,
        border: `1px solid ${style.border}`,
        borderRadius: 10,
        color: style.text,
        fontSize: '0.7rem',
        fontWeight: 400,
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        whiteSpace: 'nowrap',
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: '50%',
          background: style.dot,
          flexShrink: 0,
        }}
      />
      {displayLabel}
    </span>
  )
}

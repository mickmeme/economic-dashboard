import { useState, useEffect } from 'react'

function secsToMidnightUTC() {
  const now = new Date()
  const midnight = new Date(Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate() + 1,
  ))
  return Math.round((midnight - now) / 1000)
}

function fmt(secs) {
  if (secs <= 0) return '00:00:00'
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function MidnightCountdown() {
  const [secs, setSecs] = useState(secsToMidnightUTC)

  useEffect(() => {
    const id = setInterval(() => setSecs(secsToMidnightUTC()), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <span className="flex items-center gap-0.5 shrink-0">
      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
      <span className="text-[8px] text-[#555] font-mono tabular-nums whitespace-nowrap">
        {fmt(secs)}
      </span>
    </span>
  )
}

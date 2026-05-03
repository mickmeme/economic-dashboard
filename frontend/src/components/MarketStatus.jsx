import { useState, useEffect } from 'react'

const MARKET_HOURS = {
  '^GSPC':     { tz: 'America/New_York', open: { h: 9,  m: 30 }, close: { h: 16, m: 0  } },
  '^AXJO':     { tz: 'Australia/Sydney', open: { h: 10, m: 0  }, close: { h: 16, m: 0  } },
  '000001.SS': { tz: 'Asia/Shanghai',   open: { h: 9,  m: 30 }, close: { h: 15, m: 0  }, lunch: { start: { h: 11, m: 30 }, end: { h: 13, m: 0 } } },
  '^NSEI':     { tz: 'Asia/Kolkata',    open: { h: 9,  m: 15 }, close: { h: 15, m: 30 } },
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function toSecs({ h, m }) { return h * 3600 + m * 60 }

function getTzSnapshot(tz) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      timeZone: tz, weekday: 'short',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: false,
    }).formatToParts(new Date()).map(p => [p.type, p.value])
  )
  return {
    dow:  WEEKDAYS.indexOf(parts.weekday),
    h:    parseInt(parts.hour) % 24,
    m:    parseInt(parts.minute),
    s:    parseInt(parts.second),
  }
}

function getStatus(ticker) {
  const cfg = MARKET_HOURS[ticker]
  if (!cfg) return null

  const { dow, h, m, s } = getTzSnapshot(cfg.tz)
  const nowS   = h * 3600 + m * 60 + s
  const openS  = toSecs(cfg.open)
  const closeS = toSecs(cfg.close)

  const isWeekend = dow === 0 || dow === 6
  const inLunch   = cfg.lunch
    && nowS >= toSecs(cfg.lunch.start)
    && nowS <  toSecs(cfg.lunch.end)

  const isOpen = !isWeekend && nowS >= openS && nowS < closeS && !inLunch

  if (isOpen) {
    // Countdown to close (or to lunch if Shanghai)
    let secsUntilClose = closeS - nowS
    if (cfg.lunch) {
      const lunchStartS = toSecs(cfg.lunch.start)
      if (nowS < lunchStartS) secsUntilClose = lunchStartS - nowS
    }
    return { open: true, secs: Math.round(secsUntilClose) }
  }

  // Seconds until next open
  let secsUntilOpen
  if (!isWeekend && nowS < openS) {
    secsUntilOpen = openS - nowS
  } else if (inLunch) {
    secsUntilOpen = toSecs(cfg.lunch.end) - nowS
  } else {
    // Find next weekday (Mon–Fri)
    let ahead = 1
    while ([0, 6].includes((dow + ahead) % 7)) ahead++
    secsUntilOpen = (86400 - nowS) + (ahead - 1) * 86400 + openS
  }

  return { open: false, secs: Math.round(secsUntilOpen) }
}

function fmt(secs) {
  if (secs <= 0) return 'Opening…'
  const d = Math.floor(secs / 86400)
  const h = Math.floor((secs % 86400) / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (d > 0) return `${d}d ${h}h ${m}m`
  if (h > 0) return `${h}h ${m}m ${s}s`
  return `${m}m ${s}s`
}

export default function MarketStatus({ ticker }) {
  const [status, setStatus] = useState(() => getStatus(ticker))

  useEffect(() => {
    const id = setInterval(() => setStatus(getStatus(ticker)), 1000)
    return () => clearInterval(id)
  }, [ticker])

  if (!status) return null

  return (
    <span className="flex items-center gap-1 shrink-0">
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${status.open ? 'bg-green-400' : 'bg-red-500'}`} />
      {status.secs != null && (
        <span className="text-[8px] text-[#555] font-mono tabular-nums whitespace-nowrap">
          {fmt(status.secs)}
        </span>
      )}
    </span>
  )
}

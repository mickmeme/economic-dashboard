import { useState } from 'react'
import {
  LineChart, Line, ResponsiveContainer,
  XAxis, YAxis, Tooltip,
} from 'recharts'
import { useHistory } from '../hooks/useMarketData'

const PERIODS = [
  { key: '1d', label: '1D' },
  { key: '1w', label: '1W' },
  { key: '1m', label: '1M' },
  { key: '3m', label: '3M' },
  { key: '1y', label: '1Y' },
]

const INDICATORS = [
  { key: 'bb',  label: 'Bollinger Bands' },
  { key: 'mae', label: 'MA Envelope' },
]

const BB_PERIOD  = 20
const MAE_PERIOD = 20
const MAE_PCT    = 0.025  // ±2.5%

// Fetch a longer period to seed BB, then slice to the display window
const WARMUP_PERIOD = {
  '1d': '1d_warmup',
  '1w': '1w_warmup',
  '1m': '1m_warmup',
  '3m': '3m_warmup',
  '1y': '1y_warmup',
}

const DISPLAY_WINDOW_MS = {
  '1d':  1   * 24 * 3600 * 1000,
  '1w':  7   * 24 * 3600 * 1000,
  '1m':  30  * 24 * 3600 * 1000,
  '3m':  90  * 24 * 3600 * 1000,
  '1y':  365 * 24 * 3600 * 1000,
}

function calcBollingerBands(data) {
  return data.map((point, i) => {
    if (i < BB_PERIOD - 1) return { ...point, upper: null, middle: null, lower: null }
    const values = data.slice(i - BB_PERIOD + 1, i + 1).map(d => d.value).filter(v => v != null)
    if (values.length < BB_PERIOD) return { ...point, upper: null, middle: null, lower: null }
    const mean = values.reduce((s, v) => s + v, 0) / BB_PERIOD
    const std  = Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / BB_PERIOD)
    return {
      ...point,
      upper:  round(mean + 2 * std),
      middle: round(mean),
      lower:  round(mean - 2 * std),
    }
  })
}

function calcMAEnvelopes(data) {
  return data.map((point, i) => {
    if (i < MAE_PERIOD - 1) return { ...point, upper: null, middle: null, lower: null }
    const values = data.slice(i - MAE_PERIOD + 1, i + 1).map(d => d.value).filter(v => v != null)
    if (values.length < MAE_PERIOD) return { ...point, upper: null, middle: null, lower: null }
    const mean = values.reduce((s, v) => s + v, 0) / MAE_PERIOD
    return {
      ...point,
      upper:  round(mean * (1 + MAE_PCT)),
      middle: round(mean),
      lower:  round(mean * (1 - MAE_PCT)),
    }
  })
}

function round(v) { return Math.round(v * 100) / 100 }

function formatYAxis(v) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)     return `${(v / 1_000).toFixed(1)}k`
  return v.toFixed(2)
}

function fmt(v) {
  return v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—'
}

export default function HistoryChart({ type, id, lineColor = '#22c55e', chartClassName = 'h-48', useWarmup = true, valueLabel = 'Price' }) {
  const [period,    setPeriod]    = useState('1m')
  const [indicator, setIndicator] = useState('bb')

  const fetchPeriod = useWarmup ? (WARMUP_PERIOD[period] ?? period) : period
  const { data: history, isLoading } = useHistory(type, id, fetchPeriod)

  // All data including warmup — used for seeding the indicator calculation
  const allData = (history ?? []).map(h => ({
    time:  h.timestamp,
    value: h.close ?? h.price,
  }))

  const allWithIndicator = indicator === 'bb'
    ? calcBollingerBands(allData)
    : calcMAEnvelopes(allData)

  // Slice to the display window so only the user's chosen period is rendered.
  // useWarmup=false (e.g. bonds) skips the window filter — backend returns exactly the right range.
  const cutoffMs  = useWarmup ? Date.now() - (DISPLAY_WINDOW_MS[period] ?? Infinity) : 0
  const chartData = allWithIndicator.filter(d => new Date(d.time).getTime() >= cutoffMs)

  const latestBB      = [...chartData].reverse().find(d => d.upper != null) ?? null
  const latestPrice   = allData.length > 0 ? allData[allData.length - 1].value : null

  const isBB = indicator === 'bb'

  const stats = latestBB ? [
    {
      label: isBB ? 'Lower BB'     : `Lower (-${(MAE_PCT * 100).toFixed(1)}%)`,
      value: fmt(latestBB.lower),
      color: '#FFF97F',
    },
    {
      label: isBB ? 'SMA 20'       : `SMA ${MAE_PERIOD}`,
      value: fmt(latestBB.middle),
      color: '#888',
    },
    {
      label: isBB ? 'Upper BB'     : `Upper (+${(MAE_PCT * 100).toFixed(1)}%)`,
      value: fmt(latestBB.upper),
      color: '#FFF97F',
    },
  ] : []

  const signal = (() => {
    if (!latestBB || latestPrice == null) return null
    const label = isBB ? 'Bands' : 'Envelope'
    if (latestPrice > latestBB.upper) return { text: `Above ${label}`, color: '#ef4444' }
    if (latestPrice < latestBB.lower) return { text: `Below ${label}`, color: '#22c55e' }
    return { text: `Within ${label}`, color: '#666' }
  })()

  const tooltipLabels = {
    value:  valueLabel,
    upper:  isBB ? 'Upper BB'  : `Upper (+${(MAE_PCT * 100).toFixed(1)}%)`,
    middle: isBB ? 'SMA 20'    : `SMA ${MAE_PERIOD}`,
    lower:  isBB ? 'Lower BB'  : `Lower (-${(MAE_PCT * 100).toFixed(1)}%)`,
  }

  return (
    <div onClick={e => e.stopPropagation()}>

      {/* Controls row */}
      <div className="flex items-center justify-between gap-2 mb-4">
        {/* Period selector */}
        <div className="flex gap-1">
          {PERIODS.map(p => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              className={`text-xs px-2.5 py-1 rounded font-semibold uppercase tracking-wider transition-all duration-150 ${
                period === p.key
                  ? 'bg-[#FFF97F] text-black'
                  : 'bg-[#1A1A1A] text-[#555] hover:text-[#999] hover:bg-[#222]'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Indicator toggle */}
        <div className="flex gap-1">
          {INDICATORS.map(ind => (
            <button
              key={ind.key}
              onClick={() => setIndicator(ind.key)}
              className={`text-[10px] px-2.5 py-1 rounded font-semibold uppercase tracking-wider transition-all duration-150 ${
                indicator === ind.key
                  ? 'bg-[#FFF97F]/20 text-[#FFF97F] border border-[#FFF97F]/40'
                  : 'bg-[#1A1A1A] text-[#555] border border-transparent hover:text-[#999] hover:bg-[#222]'
              }`}
            >
              {ind.label}
            </button>
          ))}
        </div>
      </div>

      {/* Band stats row */}
      {latestBB && (
        <div className="flex items-center gap-6 mb-4 px-1">
          {stats.map(s => (
            <div key={s.label}>
              <p className="text-[9px] text-[#555] uppercase tracking-wider mb-0.5">{s.label}</p>
              <p className="text-xs font-mono" style={{ color: s.color }}>{s.value}</p>
            </div>
          ))}
          {signal && (
            <div className="ml-auto text-right">
              <p className="text-[9px] text-[#555] uppercase tracking-wider mb-0.5">Position</p>
              <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: signal.color }}>
                {signal.text}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Chart */}
      <div className={chartClassName}>
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <span className="text-[#333] text-sm">Loading chart…</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
              <XAxis dataKey="time" hide />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#444', fontSize: 10 }}
                width={52}
                tickFormatter={formatYAxis}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#141414',
                  border: '1px solid #2A2A2A',
                  borderRadius: '6px',
                  fontSize: '11px',
                  padding: '8px 12px',
                }}
                labelFormatter={(label) => {
                  const d = new Date(label)
                  if (isNaN(d)) return label
                  const showTime = period === '1d' || period === '1w'
                  return d.toLocaleString(undefined, showTime
                    ? { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
                    : { month: 'short', day: 'numeric', year: 'numeric' }
                  )
                }}
                labelStyle={{ color: '#888', fontSize: '10px', marginBottom: '4px' }}
                itemSorter={(item) => -(item.value ?? 0)}
                formatter={(v, name) => [
                  v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—',
                  tooltipLabels[name] ?? name,
                ]}
              />
              <Line type="monotone" dataKey="upper"  stroke="#FFF97F" strokeWidth={1} strokeDasharray="4 4" strokeOpacity={0.5} dot={false} connectNulls={false} />
              <Line type="monotone" dataKey="middle" stroke="#555"    strokeWidth={1} strokeDasharray="3 5" dot={false} connectNulls={false} />
              <Line type="monotone" dataKey="lower"  stroke="#FFF97F" strokeWidth={1} strokeDasharray="4 4" strokeOpacity={0.5} dot={false} connectNulls={false} />
              <Line type="monotone" dataKey="value"  stroke={lineColor} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

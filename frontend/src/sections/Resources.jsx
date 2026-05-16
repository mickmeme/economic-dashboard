import { useState } from 'react'
import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import { useResourcesList, useResourceHistory } from '../hooks/useMarketData'

const PERIODS = [
  { key: '1d', label: '1D' },
  { key: '1w', label: '1W' },
  { key: '1m', label: '1M' },
  { key: '3m', label: '3M' },
  { key: '1y', label: '1Y' },
  { key: '5y', label: '5Y' },
]

function fmtPrice(price, unit) {
  if (price == null) return '—'
  // Gas can be < $10, palladium > $1000 — just format sensibly
  if (price < 10)   return `$${price.toFixed(3)}`
  if (price < 100)  return `$${price.toFixed(2)}`
  return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function xLabel(v, period) {
  const d = new Date(v)
  if (isNaN(d)) return ''
  if (period === '1d')
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  if (period === '1w')
    return d.toLocaleDateString(undefined, { weekday: 'short' })
  if (period === '1m' || period === '3m')
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return d.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
}

function yLabel(v) {
  if (v == null) return ''
  if (v >= 1000) return `$${(v / 1000).toFixed(1)}k`
  if (v < 10)   return `$${v.toFixed(2)}`
  return `$${v.toFixed(0)}`
}

function fmtVolume(v) {
  if (!v) return '0'
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)     return `${(v / 1_000).toFixed(0)}K`
  return String(v)
}

function SupplyBar({ supply, consumption, color }) {
  const { pct_mined, pct_remaining, mined_label, remaining_label, source } = supply
  return (
    <div className="px-4 pb-4 pt-3 border-t border-[#1e1e1e] space-y-3">
      {/* Depletion bar */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-[#555] mb-2">
          Global Supply Depletion
        </p>
        <div className="flex items-center gap-2 mb-1.5">
          <div className="flex-1 h-2 bg-[#1e1e1e] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${pct_mined}%`, backgroundColor: color }}
            />
          </div>
          <span className="text-xs font-bold text-white w-16 text-right shrink-0">
            {pct_mined}% mined
          </span>
        </div>
        <div className="flex justify-between text-[10px] text-[#444] leading-relaxed">
          <span className="pr-4">{mined_label}</span>
          <span className="text-right shrink-0">{pct_remaining}% left · {remaining_label.split(' in ')[0]}</span>
        </div>
        <p className="text-[9px] text-[#333] mt-0.5">Source: {source}</p>
      </div>

      {/* Consumption fact */}
      {consumption && (
        <div className="border-t border-[#1a1a1a] pt-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-[#555] mb-1.5">
            Est. Global Daily Usage
          </p>
          <p className="text-sm font-bold text-white">{consumption.daily}</p>
          <p className="text-[10px] text-[#444] mt-0.5">{consumption.annual}</p>
          <p className="text-[9px] text-[#333] mt-0.5">Source: {consumption.source}</p>
        </div>
      )}
    </div>
  )
}

function ResourceCard({ resource }) {
  const [period, setPeriod] = useState('1m')
  const { data, isLoading, error } = useResourceHistory(resource.key, period)

  const changePos = resource.change_pct != null && resource.change_pct >= 0

  return (
    <div className="bg-[#141414] border border-[#222] rounded-lg flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between px-4 pt-4 pb-3">
        <div>
          <h3 className="text-sm font-bold text-white">{resource.name}</h3>
          <p className="text-[10px] text-[#555] uppercase tracking-wider mt-0.5">{resource.unit}</p>
        </div>
        <div className="text-right">
          <p className="text-xl font-bold font-mono" style={{ color: resource.color }}>
            {fmtPrice(resource.price)}
          </p>
          {resource.change_pct != null && (
            <p className={`text-[11px] font-semibold mt-0.5 ${changePos ? 'text-green-400' : 'text-red-400'}`}>
              {changePos ? '▲' : '▼'} {changePos ? '+' : ''}{resource.change_pct.toFixed(2)}%
            </p>
          )}
        </div>
      </div>

      {/* Period selector */}
      <div className="flex gap-1 px-4 mb-3">
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

      {/* Chart */}
      <div className="h-52 px-1">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <span className="text-[#333] text-sm">Loading…</span>
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center">
            <span className="text-red-400 text-sm text-center px-4">Failed to load chart</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 4 }}>
              <XAxis
                dataKey="time"
                tick={{ fill: '#444', fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => xLabel(v, period)}
                minTickGap={45}
              />
              {/* Price axis (left) */}
              <YAxis
                yAxisId="price"
                orientation="left"
                domain={['auto', 'auto']}
                tick={{ fill: '#444', fontSize: 10 }}
                width={54}
                tickFormatter={yLabel}
              />
              {/* Volume axis (right) — hidden ticks, just scales the bars */}
              <YAxis
                yAxisId="volume"
                orientation="right"
                tick={false}
                axisLine={false}
                tickLine={false}
                width={0}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#141414',
                  border: '1px solid #2A2A2A',
                  borderRadius: '6px',
                  fontSize: '11px',
                  padding: '8px 12px',
                }}
                labelFormatter={label => {
                  const d = new Date(label)
                  return isNaN(d) ? label : d.toLocaleDateString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric',
                    ...(period === '1d' ? { hour: '2-digit', minute: '2-digit' } : {}),
                  })
                }}
                labelStyle={{ color: '#888', fontSize: '10px', marginBottom: '4px' }}
                formatter={(v, name) =>
                  name === 'volume'
                    ? [fmtVolume(v), 'Volume']
                    : [fmtPrice(v), resource.name]
                }
              />
              {/* Volume bars behind price line */}
              <Bar
                yAxisId="volume"
                dataKey="volume"
                fill="#2a2a2a"
                opacity={0.8}
                isAnimationActive={false}
              />
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="value"
                stroke={resource.color}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Supply depletion */}
      <div className="mt-auto">
        <SupplyBar supply={resource.supply} consumption={resource.consumption} color={resource.color} />
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-[#141414] border border-[#222] rounded-lg p-4">
      <div className="flex justify-between mb-4">
        <div className="space-y-2">
          <div className="h-4 w-28 bg-[#1e1e1e] rounded animate-pulse" />
          <div className="h-3 w-20 bg-[#1a1a1a] rounded animate-pulse" />
        </div>
        <div className="h-7 w-20 bg-[#1e1e1e] rounded animate-pulse" />
      </div>
      <div className="h-52 bg-[#1a1a1a] rounded animate-pulse" />
    </div>
  )
}

export default function Resources() {
  const { data: resources, isLoading, error } = useResourcesList()

  if (error) {
    return (
      <div className="flex items-center justify-center h-40">
        <p className="text-red-400 text-sm">Failed to load resources data</p>
      </div>
    )
  }

  const list = resources ?? []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white mb-1">Global Commodities</h2>
        <p className="text-[#555] text-sm">
          Live prices with historical charts · Global supply depletion estimates · Source: Yahoo Finance / USGS / BP
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {isLoading
          ? [...Array(7)].map((_, i) => <SkeletonCard key={i} />)
          : list.map(r => <ResourceCard key={r.key} resource={r} />)
        }
      </div>

      <p className="text-[#333] text-xs pb-2">
        Supply depletion figures are geological estimates based on proven economically recoverable reserves vs cumulative historical production.
        Coal price uses Peabody Energy (BTU) as a coal sector market indicator — no standardised coal futures are available on Yahoo Finance.
        All figures subject to revision as exploration and extraction technology evolves.
      </p>
    </div>
  )
}

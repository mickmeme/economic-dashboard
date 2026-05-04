import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { useYieldSpread } from '../hooks/useMarketData'

const PERIODS = [
  { key: '1y',  label: '1Y'  },
  { key: '3y',  label: '3Y'  },
  { key: '5y',  label: '5Y'  },
  { key: '10y', label: '10Y' },
  { key: 'max', label: 'MAX' },
]

const TOOLTIP_LABELS = {
  earnings_yield: 'Earnings Yield',
  treasury_2y:    '2Y Treasury',
}

export default function YieldSpreadChart() {
  const [period, setPeriod] = useState('5y')
  const { data, isLoading, error } = useYieldSpread(period)

  const latest = data?.[data.length - 1] ?? null
  const spreadPositive = latest?.spread != null && latest.spread > 0

  const chartData = (data ?? []).map(d => ({
    time:          d.timestamp,
    earnings_yield: d.earnings_yield,
    treasury_2y:   d.treasury_2y,
  }))

  return (
    <div className="bg-[#141414] border border-[#222] rounded-lg p-4 xl:col-span-2">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">Earnings Yield vs 2Y Treasury</h3>
          <p className="text-[10px] text-[#555] uppercase tracking-wider mt-0.5">
            S&P 500 trailing earnings yield vs US 2-year government bond
          </p>
        </div>

        {latest && (
          <div className="flex gap-6 shrink-0">
            <div className="text-right">
              <p className="text-[9px] text-[#555] uppercase tracking-wider mb-0.5">Earnings Yield</p>
              <p className="text-xl font-bold font-mono text-[#FFF97F]">
                {latest.earnings_yield.toFixed(2)}%
              </p>
            </div>
            <div className="text-right">
              <p className="text-[9px] text-[#555] uppercase tracking-wider mb-0.5">2Y Treasury</p>
              <p className="text-xl font-bold font-mono text-[#3b82f6]">
                {latest.treasury_2y.toFixed(2)}%
              </p>
            </div>
            <div className="text-right">
              <p className="text-[9px] text-[#555] uppercase tracking-wider mb-0.5">Spread</p>
              <p
                className="text-xl font-bold font-mono"
                style={{ color: spreadPositive ? '#22c55e' : '#ef4444' }}
              >
                {latest.spread > 0 ? '+' : ''}{latest.spread.toFixed(2)}%
              </p>
              <p
                className="text-[10px] uppercase tracking-wider font-semibold mt-0.5"
                style={{ color: spreadPositive ? '#22c55e' : '#ef4444' }}
              >
                {spreadPositive ? 'Stocks Attractive' : 'Bonds Attractive'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Period selector */}
      <div className="flex gap-1 mb-4">
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
      <div className="h-56">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <span className="text-[#333] text-sm">Loading chart…</span>
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center">
            <span className="text-red-400 text-sm">Failed to load: {error.message}</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
              <XAxis
                dataKey="time"
                tick={{ fill: '#444', fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => {
                  const d = new Date(v)
                  if (isNaN(d)) return ''
                  return period === '1y' || period === '3y'
                    ? d.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
                    : String(d.getFullYear())
                }}
                minTickGap={40}
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#444', fontSize: 10 }}
                width={45}
                tickFormatter={(v) => `${v.toFixed(1)}%`}
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
                  return isNaN(d) ? label : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short' })
                }}
                labelStyle={{ color: '#888', fontSize: '10px', marginBottom: '4px' }}
                formatter={(v, name) => [`${v.toFixed(2)}%`, TOOLTIP_LABELS[name] ?? name]}
              />
              <ReferenceLine y={0} stroke="#2A2A2A" />
              <Line
                type="monotone"
                dataKey="treasury_2y"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="earnings_yield"
                stroke="#FFF97F"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-5 mt-3">
        <div className="flex items-center gap-1.5">
          <span className="w-4 h-0.5 bg-[#FFF97F] inline-block rounded" />
          <span className="text-[10px] text-[#555]">S&P 500 Earnings Yield</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-4 h-0.5 bg-[#3b82f6] inline-block rounded" />
          <span className="text-[10px] text-[#555]">US 2Y Treasury</span>
        </div>
      </div>

      <p className="text-[10px] text-[#444] mt-2 leading-relaxed">
        S&P 500 trailing 12-month earnings yield (earnings ÷ price) vs the US 2-year government bond yield.
        A positive spread means equities offer a higher yield than short-dated Treasuries — historically a sign
        stocks are attractively priced relative to bonds. When the spread turns negative, bonds yield more than stocks.
      </p>
    </div>
  )
}

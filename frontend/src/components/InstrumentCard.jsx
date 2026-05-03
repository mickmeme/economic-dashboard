import { LineChart, Line, YAxis, ResponsiveContainer } from 'recharts'
import { useHistory } from '../hooks/useMarketData'
import MarketStatus from './MarketStatus'
import MidnightCountdown from './MidnightCountdown'

function DominanceBadge({ dominance, change }) {
  const isUp   = change != null && change > 0
  const isDown = change != null && change < 0
  return (
    <span className="shrink-0 text-[9px] font-bold tracking-wider whitespace-nowrap leading-none">
      <span className="text-[#FFF97F]">DOM {dominance.toFixed(1)}%</span>
      {change != null && (
        <span className={isUp ? ' text-green-400' : isDown ? ' text-red-400' : ' text-[#555]'}>
          {' '}({isUp ? '+' : ''}{change.toFixed(1)}%)
        </span>
      )}
    </span>
  )
}

function formatFlow(value) {
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(2)}B`
  if (value >= 1_000_000)     return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000)         return `$${(value / 1_000).toFixed(1)}K`
  return `$${value.toFixed(0)}`
}

export default function InstrumentCard({ instrument, period, onSelect }) {
  const isIndex  = instrument.section !== 'crypto'
  const histId   = isIndex ? instrument.ticker : instrument.id
  const histType = isIndex ? 'indices' : 'crypto'

  const { data: sparkData } = useHistory(histType, histId, period)

  const sparkChartData = (sparkData ?? []).map(h => ({
    value: h.close ?? h.price,
  }))

  const periodChange = (() => {
    if (sparkChartData.length < 2) return instrument.change_percent
    const first = sparkChartData[0].value
    const last  = sparkChartData[sparkChartData.length - 1].value
    if (!first || !last) return instrument.change_percent
    return Math.round(((last - first) / first) * 10000) / 100
  })()

  const change     = periodChange
  const isPositive = change > 0
  const isNegative = change < 0
  const lineColor  = isNegative ? '#ef4444' : '#22c55e'

  const displayId = instrument.ticker ?? instrument.symbol

  // Dominance change: compare period-start market cap to current dominance
  const dominanceChange = (() => {
    if (isIndex || !sparkData || sparkData.length < 2) return null
    if (instrument.dominance == null || !instrument.total_market_cap) return null
    const startMarketCap = sparkData[0]?.market_cap
    if (!startMarketCap) return null
    const startDominance = (startMarketCap / instrument.total_market_cap) * 100
    return Math.round((instrument.dominance - startDominance) * 100) / 100
  })()

  const flows = (() => {
    if (isIndex || !sparkData || sparkData.length < 2) return null
    let inflow = 0, outflow = 0
    for (let i = 1; i < sparkData.length; i++) {
      const delta = sparkData[i].price - sparkData[i - 1].price
      const vol   = sparkData[i].volume ?? 0
      if (delta > 0) inflow  += vol
      else           outflow += vol
    }
    const net = inflow - outflow
    return { net, isInflow: net >= 0 }
  })()

  return (
    <div className="bg-[#141414] border border-[#222] rounded-lg p-3 hover:border-[#FFF97F] transition-all duration-200 flex flex-col gap-0.5 cursor-pointer" onClick={() => onSelect?.(instrument)}>
      <div className="flex items-stretch gap-2">
        {/* Left: name + inline ring / ticker / price */}
        <div className="flex flex-col justify-between min-w-0 flex-1">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-xs font-semibold text-white leading-tight truncate">{instrument.name}</span>
            {!isIndex && instrument.dominance != null && (
              <DominanceBadge dominance={instrument.dominance} change={dominanceChange} />
            )}
          </div>
          <span className="text-[10px] text-[#444] font-mono uppercase tracking-wider truncate mt-0.5">{displayId}</span>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="text-sm font-bold text-white leading-tight">
              {instrument.price != null
                ? instrument.price.toLocaleString(undefined, { maximumFractionDigits: 2 })
                : '—'}
              <span className="text-[10px] text-[#3A3A3A] font-normal ml-1">{instrument.currency}</span>
            </span>
            {instrument.section === 'global' && (
              <MarketStatus ticker={instrument.ticker} />
            )}
            {instrument.section === 'au_sectors' && (
              <MarketStatus ticker="^AXJO" />
            )}
            {!isIndex && <MidnightCountdown />}
          </div>
        </div>

        {/* Right: change badge + sparkline */}
        <div className="flex flex-col items-end gap-1 shrink-0 w-16">
          {change != null && (
            <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
              isPositive ? 'bg-green-950/60 text-green-400'
              : isNegative ? 'bg-red-950/60 text-red-400'
              : 'bg-[#1E1E1E] text-[#555]'
            }`}>
              {isPositive ? '+' : ''}{change}%
            </span>
          )}
          {sparkChartData.length > 0 && (
            <div className="w-full flex-1">
              <ResponsiveContainer width="100%" height={36}>
                <LineChart data={sparkChartData}>
                  <YAxis domain={['auto', 'auto']} hide />
                  <Line type="monotone" dataKey="value" stroke={lineColor} dot={false} strokeWidth={1.5} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {flows && (
        <div className={`flex items-center gap-1 pt-1.5 mt-1 border-t border-[#1C1C1C] text-[10px] font-mono ${flows.isInflow ? 'text-green-500' : 'text-red-500'}`}>
          <span>{flows.isInflow ? '↑' : '↓'}</span>
          <span>{formatFlow(Math.abs(flows.net))}</span>
          <span className="uppercase tracking-wider">{flows.isInflow ? 'Inflow' : 'Outflow'}</span>
        </div>
      )}
    </div>
  )
}

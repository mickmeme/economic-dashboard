import { useEffect } from 'react'
import HistoryChart from './HistoryChart'

export default function InstrumentModal({ instrument, onClose }) {
  const isCrypto = instrument.section === 'crypto'
  const id       = isCrypto ? instrument.id : instrument.ticker
  const type     = isCrypto ? 'crypto' : instrument.section === 'bonds' ? 'bonds' : 'indices'
  const isYield  = instrument.currency === '%'

  const isPositive = (instrument.change_percent ?? 0) > 0
  const isNegative = (instrument.change_percent ?? 0) < 0

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  // Prevent body scroll while modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-[#141414] border border-[#2A2A2A] rounded-lg overflow-hidden shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Yellow top border */}
        <div className="h-[3px] bg-[#FFF97F]" />

        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-5 pb-4 border-b border-[#1C1C1C]">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-[#555] uppercase tracking-widest">
                {instrument.ticker ?? instrument.symbol}
              </span>
              <span className="text-[10px] text-[#333] uppercase tracking-widest">
                {instrument.currency}
              </span>
            </div>
            <h2 className="text-lg font-bold text-white uppercase tracking-tight">
              {instrument.name}
            </h2>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-3xl font-bold text-white">
                {instrument.price != null
                  ? isYield
                    ? `${instrument.price.toFixed(2)}%`
                    : instrument.price.toLocaleString(undefined, { maximumFractionDigits: 2 })
                  : '—'}
              </span>
              {instrument.change_percent != null && (
                <span className={`text-sm font-bold px-2 py-1 rounded ${
                  isPositive ? 'bg-green-950/60 text-green-400'
                  : isNegative ? 'bg-red-950/60 text-red-400'
                  : 'bg-[#1E1E1E] text-[#555]'
                }`}>
                  {isPositive ? '+' : ''}{instrument.change_percent.toFixed(2)}%
                </span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-[#444] hover:text-[#FFF97F] transition-colors text-lg leading-none mt-1 p-1"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Chart */}
        <div className="px-6 py-5">
          <HistoryChart
            type={type}
            id={id}
            lineColor={isNegative ? '#ef4444' : '#22c55e'}
            chartClassName="h-72"
            useWarmup={!isYield}
            valueLabel={isYield ? 'Rate (% p.a.)' : 'Price'}
          />
        </div>
      </div>
    </div>
  )
}

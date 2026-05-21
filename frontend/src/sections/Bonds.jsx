import { useState } from 'react'
import InstrumentCard from '../components/InstrumentCard'
import { CardSkeleton } from '../components/LoadingSkeleton'
import { useBonds } from '../hooks/useMarketData'

const MATURITIES = ['3Y', '5Y', '10Y']

export default function Bonds({ period, onSelect }) {
  const { data, isLoading, error } = useBonds()
  const [maturity, setMaturity] = useState('10Y')

  const filtered = (data ?? []).filter(b => b.maturity === maturity)
  const skeletonCount = maturity === '10Y' ? 4 : 1

  return (
    <section className="mb-4">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
        <h2 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em] whitespace-nowrap">
          Bonds
        </h2>
        <div className="flex gap-1 ml-1">
          {MATURITIES.map(m => (
            <button
              key={m}
              onClick={() => setMaturity(m)}
              className={`text-[9px] px-2 py-0.5 rounded font-semibold uppercase tracking-wider transition-all duration-150 ${
                maturity === m
                  ? 'bg-[#FFF97F] text-black'
                  : 'bg-[#1A1A1A] text-[#555] hover:text-[#999] hover:bg-[#222]'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
        <div className="flex-1 h-px bg-[#1C1C1C]" />
      </div>
      <div className={`grid gap-2 ${maturity === '10Y' ? 'grid-cols-2 lg:grid-cols-4' : 'grid-cols-2 lg:grid-cols-4'}`}>
        {isLoading
          ? Array.from({ length: skeletonCount }).map((_, i) => <CardSkeleton key={i} />)
          : filtered.map(inst => (
              <InstrumentCard key={inst.ticker} instrument={inst} period={period} onSelect={onSelect} />
            ))}
      </div>
      {error && (
        <p className="text-red-400 text-sm mt-2">Failed to load: {error.message}</p>
      )}
    </section>
  )
}

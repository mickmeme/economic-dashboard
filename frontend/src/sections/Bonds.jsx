import InstrumentCard from '../components/InstrumentCard'
import { CardSkeleton } from '../components/LoadingSkeleton'
import { useBonds } from '../hooks/useMarketData'

export default function Bonds({ period, onSelect }) {
  const { data, isLoading, error } = useBonds()

  return (
    <section className="mb-4">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
        <h2 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em] whitespace-nowrap">
          Bonds
        </h2>
        <div className="flex-1 h-px bg-[#1C1C1C]" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
          : (data ?? []).map(inst => (
              <InstrumentCard key={inst.ticker} instrument={inst} period={period} onSelect={onSelect} />
            ))}
      </div>
      {error && (
        <p className="text-red-400 text-sm mt-2">Failed to load: {error.message}</p>
      )}
    </section>
  )
}

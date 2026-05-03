import InstrumentCard from '../components/InstrumentCard'
import { CardSkeleton } from '../components/LoadingSkeleton'
import PepeEmoji from '../components/PepeEmoji'
import { useIndices } from '../hooks/useMarketData'

export default function GlobalIndices({ period, onSelect }) {
  const { data, isLoading, error } = useIndices()
  const instruments = data?.filter(d => d.section === 'global') ?? []

  const avgChange = (() => {
    const changes = instruments.map(i => i.change_percent).filter(c => c != null)
    if (changes.length === 0) return null
    return changes.reduce((s, c) => s + c, 0) / changes.length
  })()

  const pepeSrc   = avgChange == null || avgChange >= 0 ? '/characters/pepe-rich.png' : '/characters/pepe-laugh.png'
  const pepeTitle = avgChange == null ? 'Global markets' : avgChange >= 0 ? 'Markets are up — Pepe is rich' : 'Markets are down — Pepe is laughing'

  return (
    <section className="mb-4">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
        <h2 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em] whitespace-nowrap">
          Global Indices
        </h2>
        <div className="flex-1 h-px bg-[#1C1C1C]" />
        {!isLoading && (
          <PepeEmoji src={pepeSrc} size={36} title={pepeTitle} />
        )}
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
          : instruments.map(inst => <InstrumentCard key={inst.ticker} instrument={inst} period={period} onSelect={onSelect} />)}
      </div>
      {error && (
        <p className="text-red-400 text-sm mt-2">Failed to load: {error.message}</p>
      )}
    </section>
  )
}

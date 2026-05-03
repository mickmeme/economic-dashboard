import SectionHeader from '../components/SectionHeader'
import InstrumentCard from '../components/InstrumentCard'
import { CardSkeleton } from '../components/LoadingSkeleton'
import PepeEmoji from '../components/PepeEmoji'
import { useCrypto } from '../hooks/useMarketData'

export default function Crypto({ period, onSelect }) {
  const { data, isLoading, error } = useCrypto()

  const avgChange = (() => {
    if (!data || data.length === 0) return null
    const changes = data.map(c => c.change_percent).filter(c => c != null)
    if (changes.length === 0) return null
    return changes.reduce((s, c) => s + c, 0) / changes.length
  })()

  const pepeSrc = avgChange == null
    ? '/characters/pepe-money.png'
    : avgChange >= 0
      ? '/characters/pepe-rich.png'
      : '/characters/pepe-laugh.png'

  const pepeTitle = avgChange == null
    ? 'Crypto Pepe'
    : avgChange >= 0
      ? 'Crypto is up — Pepe is rich'
      : 'Crypto is down — Pepe is laughing at the bears'

  return (
    <section className="mb-4">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
        <h2 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em] whitespace-nowrap">
          Cryptocurrency
        </h2>
        <div className="flex-1 h-px bg-[#1C1C1C]" />
        {!isLoading && (
          <PepeEmoji src={pepeSrc} size={36} title={pepeTitle} />
        )}
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
          : (data ?? []).map(inst => <InstrumentCard key={inst.id} instrument={inst} period={period} onSelect={onSelect} />)}
      </div>
      {error && (
        <p className="text-red-400 text-sm mt-2">Failed to load: {error.message}</p>
      )}
    </section>
  )
}

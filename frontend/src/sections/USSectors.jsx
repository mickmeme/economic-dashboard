import SectionHeader from '../components/SectionHeader'
import InstrumentCard from '../components/InstrumentCard'
import { CardSkeleton } from '../components/LoadingSkeleton'
import { useIndices } from '../hooks/useMarketData'

export default function USSectors({ period, onSelect }) {
  const { data, isLoading, error } = useIndices()
  const instruments = data?.filter(d => d.section === 'us_sectors') ?? []

  return (
    <section className="mb-4">
      <SectionHeader title="US Sectors" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 gap-2">
        {isLoading
          ? Array.from({ length: 8 }).map((_, i) => <CardSkeleton key={i} />)
          : instruments.map(inst => <InstrumentCard key={inst.ticker} instrument={inst} period={period} onSelect={onSelect} />)}
      </div>
      {error && (
        <p className="text-red-400 text-sm mt-2">Failed to load: {error.message}</p>
      )}
    </section>
  )
}

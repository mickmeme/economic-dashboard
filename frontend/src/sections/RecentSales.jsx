import { useRecentSales } from '../hooks/useMarketData'

const SUBURBS = [
  { postcode: '3030', label: 'Point Cook' },
  { postcode: '4227', label: 'Varsity Lakes' },
]

function fmtDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d)) return dateStr
  return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
}

function SaleCard({ sale }) {
  const meta = [
    sale.property_type,
    sale.bedrooms != null ? `${sale.bedrooms} bd` : null,
    sale.bathrooms != null ? `${sale.bathrooms} ba` : null,
    sale.carspaces != null ? `${sale.carspaces} car` : null,
  ].filter(Boolean).join(' · ')

  return (
    <div className="bg-[#111] border border-[#1C1C1C] rounded p-3 flex flex-col gap-1.5">
      {meta && (
        <p className="text-[9px] text-[#555] uppercase tracking-wider">{meta}</p>
      )}
      <p className="text-[12px] text-[#CCC] leading-snug">{sale.address}</p>
      <div className="flex items-center justify-between gap-2 mt-0.5">
        <span className="text-[13px] font-bold font-mono text-[#FFF97F]">
          {sale.display_price}
        </span>
        <span className="text-[10px] text-[#444]">{fmtDate(sale.date_sold)}</span>
      </div>
    </div>
  )
}

function SaleCardSkeleton() {
  return (
    <div className="bg-[#111] border border-[#1C1C1C] rounded p-3 flex flex-col gap-2">
      <div className="h-2 w-24 bg-[#1A1A1A] rounded animate-pulse" />
      <div className="h-3 w-full bg-[#1A1A1A] rounded animate-pulse" />
      <div className="h-3 w-3/4 bg-[#1A1A1A] rounded animate-pulse" />
      <div className="flex justify-between mt-1">
        <div className="h-3 w-20 bg-[#1A1A1A] rounded animate-pulse" />
        <div className="h-3 w-16 bg-[#1A1A1A] rounded animate-pulse" />
      </div>
    </div>
  )
}

function SuburbSales({ postcode, label }) {
  const { data, isLoading, error } = useRecentSales(postcode)

  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
        <h3 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em]">
          {label}
          <span className="text-[#333] ml-1.5">{postcode}</span>
        </h3>
      </div>

      {error ? (
        <p className="text-red-400 text-xs">{error.message}</p>
      ) : (
        <div className="flex flex-col gap-2">
          {isLoading
            ? Array.from({ length: 5 }).map((_, i) => <SaleCardSkeleton key={i} />)
            : (data ?? []).length === 0
              ? <p className="text-[#444] text-sm">No recent sales found.</p>
              : (data ?? []).map((sale, i) => <SaleCard key={i} sale={sale} />)
          }
        </div>
      )}
    </div>
  )
}

export default function RecentSales() {
  return (
    <section className="mb-8">
      <div className="flex items-center gap-3 mb-4">
        <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
        <h2 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em]">
          Recent Sales
        </h2>
        <div className="flex-1 h-px bg-[#1C1C1C]" />
        <span className="text-[9px] text-[#333] uppercase tracking-wider">via Domain</span>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        {SUBURBS.map(s => (
          <SuburbSales key={s.postcode} postcode={s.postcode} label={s.label} />
        ))}
      </div>
    </section>
  )
}

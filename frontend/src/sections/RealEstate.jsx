import { useState } from 'react'
import { useRealEstateStates, useRealEstateSuburbs } from '../hooks/useMarketData'

const PROPERTY_TYPES = [
  { key: 'unit',            label: 'Unit / Apt',    sublabel: '' },
  { key: 'townhouse',       label: 'Townhouse',     sublabel: '' },
  { key: 'house_small',     label: 'Small House',   sublabel: '< 3 bed' },
  { key: 'house_large',     label: 'Large House',   sublabel: '> 3 bed' },
  { key: 'house_very_large',label: 'Very Large',    sublabel: '5 bed / 5 bath' },
]

function fmt(n) {
  if (n == null) return '—'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000)     return `$${Math.round(n / 1_000)}K`
  return `$${n}`
}

function Change({ value }) {
  if (value == null) return <span className="text-[#444] text-xs">—</span>
  const pos = value >= 0
  return (
    <span className={`text-xs font-semibold ${pos ? 'text-green-400' : 'text-red-400'}`}>
      {pos ? '▲' : '▼'} {pos ? '+' : ''}{value.toFixed(1)}%
    </span>
  )
}

function PriceCell({ stats, changeKey, change }) {
  if (!stats) {
    return (
      <td className="px-3 py-3 text-center">
        <span className="text-[#444] text-sm">—</span>
      </td>
    )
  }
  return (
    <td className="px-3 py-3 text-center">
      <div className="font-semibold text-white text-sm">{fmt(stats.median)}</div>
      <div className="text-[#555] text-xs mt-0.5">
        {fmt(stats.min)} – {fmt(stats.max)}
      </div>
      <div className="mt-1">
        <Change value={change?.[changeKey ?? 'median']} />
      </div>
    </td>
  )
}

function SkeletonRow() {
  return (
    <tr className="border-b border-[#1a1a1a]">
      <td className="px-3 py-3">
        <div className="h-4 w-28 bg-[#1C1C1C] rounded animate-pulse" />
      </td>
      {[...Array(5)].map((_, i) => (
        <td key={i} className="px-3 py-3 text-center">
          <div className="h-4 w-20 bg-[#1C1C1C] rounded animate-pulse mx-auto mb-1" />
          <div className="h-3 w-24 bg-[#161616] rounded animate-pulse mx-auto" />
        </td>
      ))}
    </tr>
  )
}

function StateTable({ data, isLoading, error }) {
  if (error) {
    const msg = error.message || 'Unknown error'
    const needsKey = msg.includes('503') || msg.includes('DOMAIN_CLIENT')
    return (
      <div className="bg-[#111] border border-[#1C1C1C] rounded-lg p-6 text-center">
        <p className="text-red-400 text-sm font-semibold mb-2">
          {needsKey ? 'Domain API credentials not configured' : 'Failed to load state data'}
        </p>
        {needsKey && (
          <p className="text-[#666] text-xs max-w-md mx-auto">
            Register at <span className="text-[#FFF97F]">developers.domain.com.au</span> and set{' '}
            <code className="bg-[#1C1C1C] px-1 rounded">DOMAIN_CLIENT_ID</code> and{' '}
            <code className="bg-[#1C1C1C] px-1 rounded">DOMAIN_CLIENT_SECRET</code> environment variables.
          </p>
        )}
      </div>
    )
  }

  const states = data?.states ?? []

  return (
    <div className="bg-[#111] border border-[#1C1C1C] rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[800px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-[#222]">
              <th className="px-3 py-3 text-left text-[#666] text-xs font-semibold uppercase tracking-wider w-44">
                State
              </th>
              {PROPERTY_TYPES.map(pt => (
                <th key={pt.key} className="px-3 py-3 text-center text-[#666] text-xs font-semibold uppercase tracking-wider">
                  <div>{pt.label}</div>
                  {pt.sublabel && <div className="text-[#444] normal-case font-normal">{pt.sublabel}</div>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? [...Array(8)].map((_, i) => <SkeletonRow key={i} />)
              : states.map(state => (
                  <tr key={state.key} className="border-b border-[#161616] hover:bg-[#141414] transition-colors">
                    <td className="px-3 py-3">
                      <div className="font-semibold text-white text-sm">{state.key}</div>
                      <div className="text-[#555] text-xs">{state.label}</div>
                    </td>
                    {PROPERTY_TYPES.map(pt => {
                      const typeData = state.types?.[pt.key]
                      return (
                        <PriceCell
                          key={pt.key}
                          stats={typeData?.current}
                          changeKey="median"
                          change={typeData?.change}
                        />
                      )
                    })}
                  </tr>
                ))
            }
          </tbody>
        </table>
      </div>
      <div className="px-4 py-2 border-t border-[#1a1a1a] flex justify-between items-center">
        <span className="text-[#444] text-xs">
          Median · (lowest – peak) · month-on-month change · Source: Domain.com.au
        </span>
        {data?.fetched_at && (
          <span className="text-[#444] text-xs">Data for {data.fetched_at}</span>
        )}
      </div>
    </div>
  )
}

function SuburbCard({ suburb }) {
  return (
    <div className="bg-[#111] border border-[#1C1C1C] rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-[#1C1C1C] flex items-baseline gap-2">
        <span className="font-semibold text-white">{suburb.label}</span>
        <span className="text-[#555] text-xs">{suburb.postcode} · {suburb.state}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-[#1a1a1a]">
              <th className="px-3 py-2 text-left text-[#555] text-xs font-semibold uppercase tracking-wider">
                Type
              </th>
              <th className="px-3 py-2 text-right text-[#555] text-xs font-semibold uppercase tracking-wider">
                Median
              </th>
              <th className="px-3 py-2 text-right text-[#555] text-xs font-semibold uppercase tracking-wider">
                Lowest
              </th>
              <th className="px-3 py-2 text-right text-[#555] text-xs font-semibold uppercase tracking-wider">
                Peak
              </th>
              <th className="px-3 py-2 text-right text-[#555] text-xs font-semibold uppercase tracking-wider">
                MoM
              </th>
            </tr>
          </thead>
          <tbody>
            {PROPERTY_TYPES.map(pt => {
              const td = suburb.types?.[pt.key]
              const curr = td?.current
              const change = td?.change
              return (
                <tr key={pt.key} className="border-b border-[#161616] hover:bg-[#141414] transition-colors">
                  <td className="px-3 py-2.5">
                    <div className="text-white text-xs font-semibold">{pt.label}</div>
                    {pt.sublabel && <div className="text-[#444] text-xs">{pt.sublabel}</div>}
                  </td>
                  <td className="px-3 py-2.5 text-right font-semibold text-white text-sm">
                    {curr ? fmt(curr.median) : <span className="text-[#444]">—</span>}
                  </td>
                  <td className="px-3 py-2.5 text-right text-[#888] text-sm">
                    {curr ? fmt(curr.min) : <span className="text-[#444]">—</span>}
                  </td>
                  <td className="px-3 py-2.5 text-right text-[#888] text-sm">
                    {curr ? fmt(curr.max) : <span className="text-[#444]">—</span>}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <Change value={change?.median} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SuburbSkeletonCard({ title }) {
  return (
    <div className="bg-[#111] border border-[#1C1C1C] rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-[#1C1C1C]">
        <div className="h-4 w-36 bg-[#1C1C1C] rounded animate-pulse" />
      </div>
      {[...Array(5)].map((_, i) => (
        <div key={i} className="px-3 py-2.5 border-b border-[#161616] flex justify-between">
          <div className="h-3 w-24 bg-[#1C1C1C] rounded animate-pulse" />
          <div className="h-3 w-16 bg-[#161616] rounded animate-pulse" />
        </div>
      ))}
    </div>
  )
}

export default function RealEstate() {
  const states = useRealEstateStates()
  const suburbs = useRealEstateSuburbs()

  const suburbList = suburbs.data ?? []
  const suburbsError = suburbs.error
  const suburbsLoading = suburbs.isLoading

  return (
    <div className="space-y-8">

      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-1">Australian Property Market</h2>
        <p className="text-[#555] text-sm">
          Median, lowest and peak sale prices by property type · Current month vs prior month · Source: Domain.com.au
        </p>
      </div>

      {/* State Overview */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-[#FFF97F]">
            State Overview
          </span>
          <span className="text-[#333] text-xs">— all states, all property types</span>
        </div>
        <StateTable
          data={states.data}
          isLoading={states.isLoading}
          error={states.error}
        />
      </section>

      {/* Suburb Spotlight */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-[#FFF97F]">
            Suburb Spotlight
          </span>
          <span className="text-[#333] text-xs">— Point Cook &amp; Varsity Lakes</span>
        </div>

        {suburbsError ? (
          <div className="bg-[#111] border border-[#1C1C1C] rounded-lg p-6 text-center">
            <p className="text-red-400 text-sm">Failed to load suburb data</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {suburbsLoading
              ? ['Point Cook', 'Varsity Lakes'].map(t => <SuburbSkeletonCard key={t} title={t} />)
              : suburbList.map(suburb => <SuburbCard key={suburb.key} suburb={suburb} />)
            }
          </div>
        )}
      </section>

      {/* Data note */}
      <p className="text-[#333] text-xs pb-2">
        Current month data is partial (from the 1st to today). Prior month reflects the full previous calendar month.
        Very large house (5 bed / 5 bath) may show no data in states with limited sales volume.
      </p>
    </div>
  )
}

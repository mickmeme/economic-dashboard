import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import { useRealEstateStates } from '../hooks/useMarketData'

const STATE_COLORS = {
  AUS: '#FFF97F',
  NSW: '#3b82f6',
  VIC: '#8b5cf6',
  QLD: '#f59e0b',
  SA:  '#ef4444',
  WA:  '#10b981',
  TAS: '#06b6d4',
  NT:  '#f97316',
  ACT: '#ec4899',
}

function fmtPrice(n) {
  if (n == null) return '—'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(3)}M`
  if (n >= 1_000)     return `$${Math.round(n / 1_000)}K`
  return `$${n}`
}

function fmtQuarter(q) {
  if (!q) return ''
  const [year, quarter] = q.split('-')
  return `${quarter} ${year}`
}

function yTickFmt(v) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v}`
}

function Change({ pct, abs }) {
  if (pct == null) return <span className="text-[#444] text-xs">—</span>
  const pos = pct >= 0
  return (
    <div className={`text-xs font-semibold ${pos ? 'text-green-400' : 'text-red-400'}`}>
      {pos ? '▲' : '▼'} {pos ? '+' : ''}{pct.toFixed(2)}%
      {abs != null && (
        <span className="text-[10px] font-normal ml-1 text-[#666]">
          ({pos ? '+' : ''}{fmtPrice(abs)})
        </span>
      )}
    </div>
  )
}

function buildChartData(states) {
  const quarterMap = {}
  for (const state of states) {
    for (const { quarter, value } of (state.history ?? [])) {
      if (!quarterMap[quarter]) quarterMap[quarter] = { quarter }
      quarterMap[quarter][state.key] = value
    }
  }
  return Object.values(quarterMap).sort((a, b) => a.quarter.localeCompare(b.quarter))
}

function SkeletonRow() {
  return (
    <tr className="border-b border-[#1a1a1a]">
      <td className="px-4 py-3">
        <div className="h-4 w-32 bg-[#1C1C1C] rounded animate-pulse" />
      </td>
      {[...Array(3)].map((_, i) => (
        <td key={i} className="px-4 py-3 text-right">
          <div className="h-4 w-20 bg-[#1A1A1A] rounded animate-pulse ml-auto" />
        </td>
      ))}
    </tr>
  )
}

export default function RealEstate() {
  const { data, isLoading, error } = useRealEstateStates()

  const states   = data?.states ?? []
  const period   = data?.period ?? ''
  const national = states.find(s => s.key === 'AUS')
  const byState  = states.filter(s => s.key !== 'AUS')
  const chartData = buildChartData(states)

  if (error) {
    return (
      <div className="flex items-center justify-center h-40">
        <p className="text-red-400 text-sm">Failed to load real estate data</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-white mb-1">Australian Property Market</h2>
        <p className="text-[#555] text-sm">
          Mean dwelling value by state · Quarter-on-quarter and year-on-year changes
          · Source: ABS Residential Dwelling Values (cat. 6432.0)
          {period ? ` · Latest: ${fmtQuarter(period)}` : ''}
        </p>
      </div>

      {/* National headline */}
      <div className="bg-[#111] border border-[#1C1C1C] rounded-lg px-6 py-5 flex flex-wrap gap-6 items-center">
        {isLoading ? (
          <>
            <div className="h-8 w-36 bg-[#1C1C1C] rounded animate-pulse" />
            <div className="h-5 w-24 bg-[#1a1a1a] rounded animate-pulse ml-6" />
          </>
        ) : (
          <>
            <div>
              <p className="text-[10px] uppercase tracking-wider font-semibold text-[#555] mb-1">
                National Mean Dwelling Value
              </p>
              <p className="text-3xl font-bold font-mono" style={{ color: STATE_COLORS.AUS }}>
                {fmtPrice(national?.price)}
              </p>
            </div>
            <div className="border-l border-[#222] pl-6">
              <p className="text-[10px] uppercase tracking-wider text-[#555] mb-1">Quarter-on-Quarter</p>
              <Change pct={national?.qoq_pct} abs={national?.qoq_abs} />
            </div>
            <div className="border-l border-[#222] pl-6">
              <p className="text-[10px] uppercase tracking-wider text-[#555] mb-1">Year-on-Year</p>
              <Change pct={national?.yoy_pct} />
            </div>
          </>
        )}
      </div>

      {/* State breakdown table */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-[#FFF97F]">
            State Breakdown
          </span>
          <span className="text-[#333] text-xs">— mean dwelling value, quarterly changes</span>
        </div>

        <div className="bg-[#111] border border-[#1C1C1C] rounded-lg overflow-hidden">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-[#222]">
                <th className="px-4 py-3 text-left text-[#555] text-xs font-semibold uppercase tracking-wider">
                  State
                </th>
                <th className="px-4 py-3 text-right text-[#555] text-xs font-semibold uppercase tracking-wider">
                  Mean Price
                </th>
                <th className="px-4 py-3 text-right text-[#555] text-xs font-semibold uppercase tracking-wider">
                  QoQ Change
                </th>
                <th className="px-4 py-3 text-right text-[#555] text-xs font-semibold uppercase tracking-wider">
                  YoY Change
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? [...Array(8)].map((_, i) => <SkeletonRow key={i} />)
                : byState.map(state => (
                    <tr key={state.key} className="border-b border-[#161616] hover:bg-[#141414] transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: STATE_COLORS[state.key] ?? '#555' }}
                          />
                          <div>
                            <div className="font-semibold text-white">{state.key}</div>
                            <div className="text-[#555] text-xs">{state.label}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-bold font-mono text-white">{fmtPrice(state.price)}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Change pct={state.qoq_pct} abs={state.qoq_abs} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Change pct={state.yoy_pct} />
                      </td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>
      </section>

      {/* Historical chart */}
      {!isLoading && chartData.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#FFF97F]">
              Price History
            </span>
            <span className="text-[#333] text-xs">— mean dwelling value by state (quarterly)</span>
          </div>

          <div className="bg-[#111] border border-[#1C1C1C] rounded-lg p-4">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
                  <XAxis
                    dataKey="quarter"
                    tick={{ fill: '#444', fontSize: 10 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={fmtQuarter}
                    minTickGap={70}
                  />
                  <YAxis
                    tick={{ fill: '#444', fontSize: 10 }}
                    width={64}
                    tickFormatter={yTickFmt}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#141414',
                      border: '1px solid #2A2A2A',
                      borderRadius: '6px',
                      fontSize: '11px',
                      padding: '8px 12px',
                    }}
                    labelFormatter={fmtQuarter}
                    labelStyle={{ color: '#888', fontSize: '10px', marginBottom: '4px' }}
                    itemStyle={{ color: '#fff' }}
                    formatter={(v, name) => [fmtPrice(v), name === 'AUS' ? 'National' : name]}
                  />
                  {states.map(state => (
                    <Line
                      key={state.key}
                      dataKey={state.key}
                      stroke={STATE_COLORS[state.key] ?? '#666'}
                      strokeWidth={state.key === 'AUS' ? 2.5 : 1.5}
                      dot={false}
                      isAnimationActive={false}
                      name={state.key === 'AUS' ? 'National' : state.key}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3 px-1">
              {states.map(state => (
                <div key={state.key} className="flex items-center gap-1.5">
                  <div
                    className="w-4 h-0.5 rounded"
                    style={{ backgroundColor: STATE_COLORS[state.key] ?? '#555' }}
                  />
                  <span className="text-[10px] text-[#555]">
                    {state.key === 'AUS' ? 'National' : state.key}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <p className="text-[#333] text-xs pb-2">
        Mean dwelling value = total estimated value of all residential dwellings ÷ number of dwellings (ABS estimates).
        Data is quarterly; individual property type and suburb-level breakdowns are not available through this source.
        Source: Australian Bureau of Statistics, Residential Dwelling Values (cat. 6432.0).
      </p>
    </div>
  )
}

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

export default function RatioChart({
  title, subtitle, description,
  current, valuation,
  data, isLoading, error,
  periods, period, onPeriodChange,
  lineColor = '#22c55e',
  yFormatter,
  tooltipFormatter,
  referenceLines = [],
}) {
  return (
    <div className="bg-[#141414] border border-[#222] rounded-lg p-4">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">{title}</h3>
          <p className="text-[10px] text-[#555] uppercase tracking-wider mt-0.5">{subtitle}</p>
        </div>
        <div className="text-right">
          {current != null && (
            <p className="text-xl font-bold font-mono" style={{ color: valuation?.color ?? lineColor }}>
              {current}
            </p>
          )}
          {valuation && (
            <p className="text-[10px] uppercase tracking-wider font-semibold mt-0.5" style={{ color: valuation.color }}>
              {valuation.label}
            </p>
          )}
        </div>
      </div>

      <div className="flex gap-1 mb-4">
        {periods.map(p => (
          <button
            key={p.key}
            onClick={() => onPeriodChange(p.key)}
            className={`text-xs px-2.5 py-1 rounded font-semibold uppercase tracking-wider transition-all duration-150 ${
              period === p.key
                ? 'bg-[#FFF97F] text-black'
                : 'bg-[#1A1A1A] text-[#555] hover:text-[#999] hover:bg-[#222]'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="h-56">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <span className="text-[#333] text-sm">Loading chart…</span>
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center">
            <span className="text-red-400 text-sm">Failed to load: {error.message}</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
              <XAxis dataKey="time" hide />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#444', fontSize: 10 }}
                width={52}
                tickFormatter={yFormatter}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#141414',
                  border: '1px solid #2A2A2A',
                  borderRadius: '6px',
                  fontSize: '11px',
                  padding: '8px 12px',
                }}
                labelFormatter={(label) => {
                  const d = new Date(label)
                  return isNaN(d) ? label : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
                }}
                labelStyle={{ color: '#888', fontSize: '10px', marginBottom: '4px' }}
                formatter={(v) => [tooltipFormatter ? tooltipFormatter(v) : String(v), 'Ratio']}
              />
              {referenceLines.map(rl => (
                <ReferenceLine
                  key={rl.value}
                  y={rl.value}
                  stroke={rl.color}
                  strokeDasharray="5 4"
                  strokeOpacity={0.6}
                  label={{ value: rl.label, position: 'insideTopRight', fill: rl.color, fontSize: 9, fontWeight: 600 }}
                />
              ))}
              <Line type="monotone" dataKey="value" stroke={lineColor} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {description && (
        <p className="text-[10px] text-[#444] mt-3 leading-relaxed">{description}</p>
      )}
    </div>
  )
}

const PERIODS = [
  { key: '1d', label: '1D' },
  { key: '1w', label: '1W' },
  { key: '1m', label: '1M' },
  { key: '3m', label: '3M' },
  { key: '1y', label: '1Y' },
]

export default function TimeframeSelector({ period, onChange }) {
  return (
    <div className="flex items-center gap-1">
      {PERIODS.map(p => (
        <button
          key={p.key}
          onClick={() => onChange(p.key)}
          className={`text-xs px-3 py-1.5 rounded font-semibold uppercase tracking-wider transition-all duration-150 ${
            period === p.key
              ? 'bg-[#FFF97F] text-black'
              : 'bg-[#1A1A1A] text-[#555] hover:text-[#999] hover:bg-[#222]'
          }`}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}

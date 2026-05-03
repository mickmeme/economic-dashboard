import { useIsFetching } from '@tanstack/react-query'
import PepeEmoji from './PepeEmoji'

export default function Header({ lastUpdated }) {
  const isFetching = useIsFetching()

  return (
    <header className="flex items-center gap-4">
      <PepeEmoji src="/characters/pepe-analyst.png" size={52} title="Pepe is watching the markets" />
      {/* Bar-chart style geometric accent */}
      <div className="flex items-end gap-[3px] h-10 shrink-0">
        <div className="w-[3px] h-4 bg-[#FFF97F]/50 rounded-sm" />
        <div className="w-[3px] h-10 bg-[#FFF97F] rounded-sm" />
        <div className="w-[3px] h-6 bg-[#FFF97F]/70 rounded-sm" />
      </div>

      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight uppercase leading-none">
          Economic Dashboard
        </h1>
        <div className="flex items-center gap-2 mt-1.5">
          <span className="text-[10px] text-[#555] tracking-[0.2em] uppercase">
            Live Market Data
          </span>
          <span className="w-px h-3 bg-[#2A2A2A]" />
          {isFetching > 0 ? (
            <span className="text-[10px] text-[#FFF97F] animate-pulse tracking-widest uppercase">
              ● Live
            </span>
          ) : lastUpdated ? (
            <span className="text-[10px] text-[#444]">
              Updated {new Date(lastUpdated).toLocaleTimeString()}
            </span>
          ) : (
            <span className="text-[10px] text-[#444]">Loading…</span>
          )}
        </div>
      </div>
    </header>
  )
}

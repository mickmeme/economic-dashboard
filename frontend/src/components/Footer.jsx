import PepeEmoji from './PepeEmoji'

export default function Footer() {
  return (
    <footer className="bg-[#0F0F0F] border-t border-[#1C1C1C] shrink-0">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row justify-between items-center gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-end gap-[3px] h-5 shrink-0">
            <div className="w-[2px] h-2 bg-[#FFF97F]/50 rounded-sm" />
            <div className="w-[2px] h-5 bg-[#FFF97F] rounded-sm" />
            <div className="w-[2px] h-3 bg-[#FFF97F]/70 rounded-sm" />
          </div>
          <span className="text-[10px] font-bold text-[#444] uppercase tracking-[0.2em]">
            Daily Dashboard
          </span>
        </div>

        <PepeEmoji src="/characters/pepe-money.png" size={32} title="Pepe is watching your money" />
        <div className="flex items-center gap-3 text-[10px] text-[#333] uppercase tracking-wider">
          <span>Yahoo Finance</span>
          <span className="w-px h-3 bg-[#222]" />
          <span>CoinGecko</span>
          <span className="w-px h-3 bg-[#222]" />
          <span>Refreshes every 5 min</span>
        </div>
      </div>
    </footer>
  )
}

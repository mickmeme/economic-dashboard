export default function SectionHeader({ title }) {
  return (
    <div className="flex items-center gap-3 mb-3">
      <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
      <h2 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em] whitespace-nowrap">
        {title}
      </h2>
      <div className="flex-1 h-px bg-[#1C1C1C]" />
    </div>
  )
}

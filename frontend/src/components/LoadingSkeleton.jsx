export function CardSkeleton() {
  return (
    <div className="bg-[#141414] border border-[#1C1C1C] rounded-lg p-3 animate-pulse flex flex-col gap-1">
      <div className="flex items-stretch gap-2">
        <div className="flex flex-col justify-between flex-1 gap-1.5">
          <div className="h-3 bg-[#1E1E1E] rounded w-14" />
          <div className="h-4 bg-[#1E1E1E] rounded w-20" />
          <div className="h-3 bg-[#1E1E1E] rounded w-16" />
        </div>
        <div className="flex flex-col items-end gap-1 w-16">
          <div className="h-4 bg-[#1E1E1E] rounded w-12" />
          <div className="h-9 bg-[#1E1E1E] rounded w-full" />
        </div>
      </div>
    </div>
  )
}

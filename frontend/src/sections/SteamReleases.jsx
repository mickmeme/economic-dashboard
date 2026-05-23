import { useRef, useCallback, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

function useSteamReleases() {
  return useQuery({
    queryKey: ['steam', 'newreleases'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/steam/newreleases`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json()
    },
    staleTime: 25 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
    retry: 1,
  })
}

function useDragScroll() {
  const ref      = useRef(null)
  const dragging = useRef(false)
  const lastX    = useRef(0)
  const moved    = useRef(false)

  const onMouseDown = useCallback(e => {
    if (e.button !== 0) return
    e.preventDefault()
    dragging.current = true
    lastX.current    = e.clientX
    moved.current    = false
  }, [])

  useEffect(() => {
    const onMouseMove = e => {
      if (!dragging.current) return
      const dx = lastX.current - e.clientX
      lastX.current = e.clientX
      if (Math.abs(dx) > 1) moved.current = true
      ref.current.scrollLeft += dx
    }
    const onMouseUp = () => { dragging.current = false }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup',   onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup',   onMouseUp)
    }
  }, [])

  const onClickCapture = useCallback(e => {
    if (moved.current) {
      e.preventDefault()
      e.stopPropagation()
      moved.current = false
    }
  }, [])

  return { ref, onMouseDown, onClickCapture }
}

function GameCard({ game }) {
  return (
    <a
      href={game.store_url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex-shrink-0 w-44 bg-[#111] border border-[#1C1C1C] rounded overflow-hidden hover:border-[#333] transition-colors duration-150 flex flex-col select-none"
    >
      <div className="relative">
        <img
          src={game.header_image}
          alt=""
          draggable={false}
          className="w-full h-24 object-cover bg-[#1A1A1A]"
          onError={e => { e.currentTarget.style.display = 'none' }}
        />
        {game.discount > 0 && (
          <span className="absolute top-1.5 right-1.5 bg-[#4c6b22] text-[#a4d007] text-[9px] font-bold px-1.5 py-0.5 rounded">
            -{game.discount}%
          </span>
        )}
      </div>
      <div className="p-2 flex flex-col gap-1 flex-1">
        <p className="text-xs text-[#CCC] font-medium leading-snug line-clamp-2">
          {game.name}
        </p>
        <div className="mt-auto pt-1 flex items-baseline gap-1.5">
          {game.original_price && (
            <span className="text-[9px] text-[#555] line-through">{game.original_price}</span>
          )}
          <span className={`text-[11px] font-bold ${game.price === 'Free' ? 'text-[#4fc3f7]' : 'text-[#a4d007]'}`}>
            {game.price}
          </span>
        </div>
      </div>
    </a>
  )
}

function GameCardSkeleton() {
  return (
    <div className="flex-shrink-0 w-44 bg-[#111] border border-[#1C1C1C] rounded overflow-hidden">
      <div className="w-full h-24 bg-[#1A1A1A] animate-pulse" />
      <div className="p-2 flex flex-col gap-2">
        <div className="h-2.5 w-full bg-[#1A1A1A] rounded animate-pulse" />
        <div className="h-2.5 w-3/4 bg-[#1A1A1A] rounded animate-pulse" />
        <div className="h-2.5 w-12 bg-[#1A1A1A] rounded animate-pulse mt-1" />
      </div>
    </div>
  )
}

export default function SteamReleases() {
  const { data, isLoading, error } = useSteamReleases()
  const dragScroll = useDragScroll()

  return (
    <section className="mb-6">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-0.5 h-4 bg-[#a4d007] shrink-0" />
        <h2 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em] whitespace-nowrap">
          New on Steam
        </h2>
        <div className="flex-1 h-px bg-[#1C1C1C]" />
      </div>

      <div
        ref={dragScroll.ref}
        onMouseDown={dragScroll.onMouseDown}
        onClickCapture={dragScroll.onClickCapture}
        className="flex gap-3 overflow-x-auto pb-2 scrollbar-none cursor-grab"
      >
        {isLoading
          ? Array.from({ length: 8 }).map((_, i) => <GameCardSkeleton key={i} />)
          : error
            ? <p className="text-red-400 text-sm py-4">Failed to load Steam releases: {error.message}</p>
            : (data ?? []).length === 0
              ? <p className="text-[#444] text-sm py-4">No releases found.</p>
              : (data ?? []).map(game => <GameCard key={game.app_id} game={game} />)
        }
      </div>
    </section>
  )
}

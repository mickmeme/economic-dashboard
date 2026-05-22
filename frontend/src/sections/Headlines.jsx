import { useRef, useCallback } from 'react'
import { useNews } from '../hooks/useMarketData'

const SECTIONS = [
  { key: 'global',      label: 'Global News'   },
  { key: 'markets',     label: 'Markets'        },
  { key: 'gaming',      label: 'Gaming'         },
  { key: '3dprinting',  label: '3D Printing'    },
]

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function useDragScroll() {
  const ref = useRef(null)
  const state = useRef({ startX: 0, scrollLeft: 0, moved: false })

  const onPointerDown = useCallback(e => {
    if (e.button !== 0) return
    const el = ref.current
    state.current = { startX: e.clientX, scrollLeft: el.scrollLeft, moved: false }
    el.setPointerCapture(e.pointerId)
    el.style.cursor = 'grabbing'
    el.style.userSelect = 'none'
  }, [])

  const onPointerMove = useCallback(e => {
    if (!ref.current.hasPointerCapture(e.pointerId)) return
    const dx = e.clientX - state.current.startX
    if (Math.abs(dx) > 4) state.current.moved = true
    ref.current.scrollLeft = state.current.scrollLeft - dx
  }, [])

  const onPointerUp = useCallback(e => {
    const el = ref.current
    if (!el) return
    el.releasePointerCapture(e.pointerId)
    el.style.cursor = 'grab'
    el.style.userSelect = ''
  }, [])

  const onClickCapture = useCallback(e => {
    if (state.current.moved) {
      e.preventDefault()
      e.stopPropagation()
      state.current.moved = false
    }
  }, [])

  return { ref, onPointerDown, onPointerMove, onPointerUp, onClickCapture }
}

function ArticleCard({ article }) {
  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex-shrink-0 w-52 bg-[#111] border border-[#1C1C1C] rounded overflow-hidden hover:border-[#333] transition-colors duration-150 flex flex-col select-none"
    >
      <img
        src={article.image_url}
        alt=""
        draggable={false}
        className="w-full h-32 object-cover bg-[#1A1A1A]"
        onError={e => { e.currentTarget.style.display = 'none' }}
      />
      <div className="p-2.5 flex flex-col gap-1 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[9px] text-[#555] uppercase tracking-wider truncate">
            {article.source}
          </span>
          <span className="text-[9px] text-[#444] shrink-0">
            {timeAgo(article.published_at)}
          </span>
        </div>
        <p className="text-[11px] text-[#CCC] leading-[1.4] line-clamp-4">
          {article.title}
        </p>
      </div>
    </a>
  )
}

function ArticleSkeleton() {
  return (
    <div className="flex-shrink-0 w-52 bg-[#111] border border-[#1C1C1C] rounded overflow-hidden">
      <div className="w-full h-32 bg-[#1A1A1A] animate-pulse" />
      <div className="p-2.5 flex flex-col gap-2">
        <div className="h-2 w-16 bg-[#1A1A1A] rounded animate-pulse" />
        <div className="h-2 w-full bg-[#1A1A1A] rounded animate-pulse" />
        <div className="h-2 w-4/5 bg-[#1A1A1A] rounded animate-pulse" />
        <div className="h-2 w-3/5 bg-[#1A1A1A] rounded animate-pulse" />
      </div>
    </div>
  )
}

function NewsSection({ sectionKey, label }) {
  const { data, isLoading, error } = useNews(sectionKey)
  const dragScroll = useDragScroll()

  return (
    <section className="mb-6">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
        <h2 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em] whitespace-nowrap">
          {label}
        </h2>
        <div className="flex-1 h-px bg-[#1C1C1C]" />
      </div>

      <div
        ref={dragScroll.ref}
        onPointerDown={dragScroll.onPointerDown}
        onPointerMove={dragScroll.onPointerMove}
        onPointerUp={dragScroll.onPointerUp}
        onClickCapture={dragScroll.onClickCapture}
        className="flex gap-3 overflow-x-auto pb-2 scrollbar-none cursor-grab"
      >
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => <ArticleSkeleton key={i} />)
          : error
            ? <p className="text-red-400 text-sm py-4">Failed to load: {error.message}</p>
            : (data ?? []).length === 0
              ? <p className="text-[#444] text-sm py-4">No articles available.</p>
              : (data ?? []).map((a, i) => <ArticleCard key={i} article={a} />)
        }
      </div>
    </section>
  )
}

export default function Headlines() {
  return (
    <div>
      {SECTIONS.map(s => (
        <NewsSection key={s.key} sectionKey={s.key} label={s.label} />
      ))}
    </div>
  )
}

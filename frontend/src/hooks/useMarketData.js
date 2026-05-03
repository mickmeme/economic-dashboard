import { useQuery } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

async function fetchJson(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function useIndices() {
  return useQuery({
    queryKey: ['indices'],
    queryFn: () => fetchJson(`${API_BASE}/api/indices`),
    refetchInterval: 5 * 60 * 1000,
    staleTime: 4 * 60 * 1000,
    retry: 2,
  })
}

export function useCrypto() {
  return useQuery({
    queryKey: ['crypto'],
    queryFn: () => fetchJson(`${API_BASE}/api/crypto`),
    refetchInterval: 5 * 60 * 1000,
    staleTime: 4 * 60 * 1000,
    retry: 2,
  })
}

export function useHistory(type, id, period, enabled = true) {
  return useQuery({
    queryKey: [type, id, 'history', period],
    queryFn: () =>
      fetchJson(`${API_BASE}/api/${type}/${encodeURIComponent(id)}/history?period=${period}`),
    enabled: enabled && !!id,
    staleTime: 4 * 60 * 1000,
    retry: 1,
  })
}

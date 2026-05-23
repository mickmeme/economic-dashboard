import { useQuery } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

async function fetchJson(url) {
  const res = await fetch(url)
  if (!res.ok) {
    let detail = ''
    try { detail = (await res.json()).detail ?? '' } catch {}
    throw new Error(`HTTP ${res.status}${detail ? ': ' + detail : ''}`)
  }
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

export function useBonds() {
  return useQuery({
    queryKey: ['bonds'],
    queryFn: () => fetchJson(`${API_BASE}/api/bonds`),
    refetchInterval: 5 * 60 * 1000,
    staleTime: 4 * 60 * 1000,
    retry: 2,
  })
}

export function useBuffettRatio(period = '10y') {
  return useQuery({
    queryKey: ['ratios', 'buffett', period],
    queryFn: () => fetchJson(`${API_BASE}/api/ratios/buffett?period=${period}`),
    staleTime: 60 * 60 * 1000,
    retry: 2,
  })
}

export function useBtcGoldRatio(period = '1y') {
  return useQuery({
    queryKey: ['ratios', 'btc-gold', period],
    queryFn: () => fetchJson(`${API_BASE}/api/ratios/btc-gold?period=${period}`),
    staleTime: 60 * 60 * 1000,
    retry: 2,
  })
}

export function useYieldSpread(period = '5y') {
  return useQuery({
    queryKey: ['ratios', 'yield-spread', period],
    queryFn: () => fetchJson(`${API_BASE}/api/ratios/yield-spread?period=${period}`),
    staleTime: 60 * 60 * 1000,
    retry: 2,
  })
}

export function useResourcesList() {
  return useQuery({
    queryKey: ['resources', 'list'],
    queryFn: () => fetchJson(`${API_BASE}/api/resources`),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  })
}

export function useResourceHistory(key, period = '1m') {
  return useQuery({
    queryKey: ['resources', 'v2', key, period],
    queryFn: () => fetchJson(`${API_BASE}/api/resources/${key}/history?period=${period}`),
    staleTime: 5 * 60 * 1000,
    retry: 1,
    enabled: !!key,
  })
}

export function useRealEstateStates() {
  return useQuery({
    queryKey: ['realestate', 'states'],
    queryFn: () => fetchJson(`${API_BASE}/api/realestate/states`),
    staleTime: 24 * 60 * 60 * 1000,
    retry: 1,
  })
}

export function useRealEstateSuburbs() {
  return useQuery({
    queryKey: ['realestate', 'suburbs'],
    queryFn: () => fetchJson(`${API_BASE}/api/realestate/suburbs`),
    staleTime: 24 * 60 * 60 * 1000,
    retry: 1,
  })
}

export function useRecentSales(postcode) {
  return useQuery({
    queryKey: ['realestate', 'sales', postcode],
    queryFn: () => fetchJson(`${API_BASE}/api/realestate/sales/${postcode}`),
    staleTime: 60 * 60 * 1000,
    retry: 1,
  })
}

export function useNews(category) {
  return useQuery({
    queryKey: ['news', category],
    queryFn: () => fetchJson(`${API_BASE}/api/news/${category}`),
    staleTime: 25 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
    retry: 1,
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

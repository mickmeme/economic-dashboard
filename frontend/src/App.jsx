import { useState } from 'react'
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query'
import Header from './components/Header'
import Footer from './components/Footer'
import InstrumentModal from './components/InstrumentModal'
import TimeframeSelector from './components/TimeframeSelector'
import GlobalIndices from './sections/GlobalIndices'
import AustralianSectors from './sections/AustralianSectors'
import Crypto from './sections/Crypto'

const queryClient = new QueryClient()

function Dashboard() {
  const [period, setPeriod] = useState('3m')
  const [selected, setSelected] = useState(null)
  const client = useQueryClient()
  const lastUpdated = client.getQueryState(['indices'])?.dataUpdatedAt

  return (
    <div className="min-h-screen bg-[#0C0C0C] text-white font-sans flex flex-col">
      {/* Top yellow accent bar */}
      <div className="h-[3px] bg-brand shrink-0" />

      {/* Header */}
      <div className="bg-[#0F0F0F] border-b border-[#1C1C1C] shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center gap-4">
          <Header lastUpdated={lastUpdated} />
          <TimeframeSelector period={period} onChange={setPeriod} />
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        <GlobalIndices period={period} onSelect={setSelected} />
        <AustralianSectors period={period} onSelect={setSelected} />
        <Crypto period={period} onSelect={setSelected} />
        {selected && <InstrumentModal instrument={selected} onClose={() => setSelected(null)} />}
      </main>

      {/* Footer */}
      <Footer />

      {/* Bottom yellow accent bar */}
      <div className="h-[3px] bg-brand shrink-0" />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  )
}

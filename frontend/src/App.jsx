import { useState } from 'react'
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query'
import Header from './components/Header'
import Footer from './components/Footer'
import InstrumentModal from './components/InstrumentModal'
import TimeframeSelector from './components/TimeframeSelector'
import GlobalIndices from './sections/GlobalIndices'
import AustralianSectors from './sections/AustralianSectors'
import USSectors from './sections/USSectors'
import Crypto from './sections/Crypto'
import Bonds from './sections/Bonds'
import Ratios from './sections/Ratios'
import RealEstate from './sections/RealEstate'
import Resources from './sections/Resources'
import Headlines from './sections/Headlines'

const queryClient = new QueryClient()

const TABS = [
  { key: 'dashboard',   label: 'Dashboard'    },
  { key: 'ratios',      label: 'Ratios'       },
  { key: 'realestate',  label: 'Real Estate'  },
  { key: 'resources',   label: 'Resources'    },
  { key: 'headlines',   label: 'Daily Headlines' },
]

function Dashboard() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [period, setPeriod] = useState('3m')
  const [selected, setSelected] = useState(null)
  const client = useQueryClient()
  const lastUpdated = client.getQueryState(['indices'])?.dataUpdatedAt

  return (
    <div className="min-h-screen bg-[#0C0C0C] text-white font-sans flex flex-col">
      <div className="h-[3px] bg-brand shrink-0" />

      <div className="bg-[#0F0F0F] border-b border-[#1C1C1C] shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center gap-4">
          <Header lastUpdated={lastUpdated} />
          {activeTab === 'dashboard' && (
            <TimeframeSelector period={period} onChange={setPeriod} />
          )}
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex gap-0 border-t border-[#1C1C1C]">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`text-xs px-4 py-2.5 font-semibold uppercase tracking-wider transition-all duration-150 border-b-2 ${
                activeTab === tab.key
                  ? 'text-[#FFF97F] border-[#FFF97F]'
                  : 'text-[#555] border-transparent hover:text-[#999]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {activeTab === 'dashboard' ? (
          <>
            <GlobalIndices period={period} onSelect={setSelected} />
            <USSectors period={period} onSelect={setSelected} />
            <AustralianSectors period={period} onSelect={setSelected} />
            <Crypto period={period} onSelect={setSelected} />
            <Bonds period={period} onSelect={setSelected} />
            {selected && <InstrumentModal instrument={selected} onClose={() => setSelected(null)} />}
          </>
        ) : activeTab === 'ratios' ? (
          <Ratios />
        ) : activeTab === 'realestate' ? (
          <RealEstate />
        ) : activeTab === 'headlines' ? (
          <Headlines />
        ) : (
          <Resources />
        )}
      </main>

      <Footer />
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

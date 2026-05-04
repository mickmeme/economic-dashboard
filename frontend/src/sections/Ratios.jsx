import { useState } from 'react'
import RatioChart from '../components/RatioChart'
import { useBuffettRatio, useBtcGoldRatio } from '../hooks/useMarketData'

const BUFFETT_PERIODS = [
  { key: '5y',  label: '5Y'  },
  { key: '10y', label: '10Y' },
  { key: 'max', label: 'MAX' },
]

const BTC_GOLD_PERIODS = [
  { key: '1y',  label: '1Y'  },
  { key: '3y',  label: '3Y'  },
  { key: 'max', label: 'MAX' },
]

function buffettValuation(ratio) {
  if (ratio == null) return null
  if (ratio < 80)  return { label: 'Undervalued',          color: '#22c55e' }
  if (ratio < 115) return { label: 'Fair Value',            color: '#FFF97F' }
  if (ratio < 150) return { label: 'Overvalued',            color: '#f97316' }
  return                   { label: 'Significantly Overvalued', color: '#ef4444' }
}

export default function Ratios() {
  const [buffettPeriod, setBuffettPeriod] = useState('10y')
  const [btcGoldPeriod, setBtcGoldPeriod] = useState('1y')

  const buffett = useBuffettRatio(buffettPeriod)
  const btcGold = useBtcGoldRatio(btcGoldPeriod)

  const currentBuffett = buffett.data?.[buffett.data.length - 1]?.ratio
  const currentBtcGold = btcGold.data?.[btcGold.data.length - 1]?.ratio

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <RatioChart
        title="Buffett Indicator"
        subtitle="Wilshire 5000 / US Nominal GDP"
        description="Total US stock market cap relative to GDP. Warren Buffett's preferred gauge of whether the market is cheap or expensive. Above 150% is historically considered significantly overvalued."
        current={currentBuffett != null ? `${currentBuffett.toFixed(1)}%` : null}
        valuation={buffettValuation(currentBuffett)}
        data={(buffett.data ?? []).map(d => ({ time: d.timestamp, value: d.ratio }))}
        isLoading={buffett.isLoading}
        error={buffett.error}
        periods={BUFFETT_PERIODS}
        period={buffettPeriod}
        onPeriodChange={setBuffettPeriod}
        lineColor="#FFF97F"
        yFormatter={(v) => `${v.toFixed(0)}%`}
        tooltipFormatter={(v) => `${v.toFixed(1)}%`}
      />
      <RatioChart
        title="BTC / Gold Market Cap"
        subtitle="Bitcoin Market Cap ÷ Gold Market Cap"
        description="Bitcoin's market cap relative to gold's estimated total market cap (~6.8B troy oz above ground). A rising ratio reflects BTC gaining ground on gold as a store of value."
        current={currentBtcGold != null ? currentBtcGold.toFixed(4) : null}
        data={(btcGold.data ?? []).map(d => ({ time: d.timestamp, value: d.ratio }))}
        isLoading={btcGold.isLoading}
        error={btcGold.error}
        periods={BTC_GOLD_PERIODS}
        period={btcGoldPeriod}
        onPeriodChange={setBtcGoldPeriod}
        lineColor="#f97316"
        yFormatter={(v) => v.toFixed(3)}
        tooltipFormatter={(v) => v.toFixed(4)}
      />
    </div>
  )
}

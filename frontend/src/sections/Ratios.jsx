import { useState } from 'react'
import RatioChart from '../components/RatioChart'
import YieldSpreadChart from '../components/YieldSpreadChart'
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

const BUFFETT_REFERENCE_LINES = [
  { value: 100, color: '#3b82f6', label: 'Fair Value'       },
  { value: 135, color: '#f97316', label: 'Overvalued'       },
  { value: 165, color: '#ef4444', label: 'Sig. Overvalued'  },
]

function buffettValuation(ratio) {
  if (ratio == null) return null
  if (ratio < 100) return { label: 'Undervalued',             color: '#22c55e' }
  if (ratio < 135) return { label: 'Fair Value',              color: '#3b82f6' }
  if (ratio < 165) return { label: 'Overvalued',              color: '#f97316' }
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
        description="Total US stock market cap relative to GDP. Warren Buffett's preferred gauge of whether the market is cheap or expensive. Blue = fair value (100%), orange = overvalued (135%), red = significantly overvalued (165%)."
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
        referenceLines={BUFFETT_REFERENCE_LINES}
      />
      <RatioChart
        title="BTC vs Gold Market Cap"
        subtitle="Bitcoin market cap as a % of gold market cap"
        description="How large Bitcoin's market cap is relative to gold's (~6.8B troy oz above ground × gold price). 10% means BTC is one-tenth the size of gold. A rising chart means BTC is gaining ground on gold as a store of value."
        current={currentBtcGold != null ? `${(currentBtcGold * 100).toFixed(2)}%` : null}
        data={(btcGold.data ?? []).map(d => ({ time: d.timestamp, value: d.ratio * 100 }))}
        isLoading={btcGold.isLoading}
        error={btcGold.error}
        periods={BTC_GOLD_PERIODS}
        period={btcGoldPeriod}
        onPeriodChange={setBtcGoldPeriod}
        lineColor="#f97316"
        yFormatter={(v) => `${v.toFixed(1)}%`}
        tooltipFormatter={(v) => `${v.toFixed(2)}% of gold`}
      />
      <YieldSpreadChart />
    </div>
  )
}

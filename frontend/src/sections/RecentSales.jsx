const SUBURBS = [
  {
    label:    'Point Cook',
    postcode: '3030',
    state:    'VIC',
    criteria: '4–5 bed house · min 4 bath',
    sites: [
      {
        name: 'domain.com.au',
        links: [
          { type: 'For Sale',      url: 'https://www.domain.com.au/sale/point-cook-vic-3030/?bedrooms=4-5&bathrooms=4&property-types=house&view=map' },
          { type: 'Recently Sold', url: 'https://www.domain.com.au/sold-listings/point-cook-vic-3030/?bedrooms=4-5&bathrooms=4&property-types=house&view=map' },
        ],
      },
      {
        name: 'realestate.com.au',
        links: [
          { type: 'For Sale',      url: 'https://www.realestate.com.au/buy/property-house-in-point+cook,+vic+3030/map-1?numBeds=4&numBaths=4' },
          { type: 'Recently Sold', url: 'https://www.realestate.com.au/sold/property-house-in-point+cook,+vic+3030/map-1?numBeds=4&numBaths=4' },
        ],
      },
    ],
  },
  {
    label:    'Varsity Lakes',
    postcode: '4227',
    state:    'QLD',
    criteria: '3 bed townhouse · min 2 bath',
    sites: [
      {
        name: 'domain.com.au',
        links: [
          { type: 'For Sale',      url: 'https://www.domain.com.au/sale/varsity-lakes-qld-4227/?bedrooms=3&bathrooms=2&property-types=townhouse&view=map' },
          { type: 'Recently Sold', url: 'https://www.domain.com.au/sold-listings/varsity-lakes-qld-4227/?bedrooms=3&bathrooms=2&property-types=townhouse&view=map' },
        ],
      },
      {
        name: 'realestate.com.au',
        links: [
          { type: 'For Sale',      url: 'https://www.realestate.com.au/buy/property-townhouse-in-varsity+lakes,+qld+4227/map-1?numBeds=3&numBaths=2' },
          { type: 'Recently Sold', url: 'https://www.realestate.com.au/sold/property-townhouse-in-varsity+lakes,+qld+4227/map-1?numBeds=3&numBaths=2' },
        ],
      },
    ],
  },
]

const SITE_THEME = {
  'domain.com.au': {
    heading:      '#60a5fa',
    forSale:      { from: '#1d4ed8', to: '#0c1f6e', press: '#071248' },
    recentlySold: { from: '#1e3a8a', to: '#0a1540', press: '#060e2a' },
  },
  'realestate.com.au': {
    heading:      '#f87171',
    forSale:      { from: '#b91c1c', to: '#5a0a0a', press: '#3b0606' },
    recentlySold: { from: '#991b1b', to: '#450808', press: '#2d0505' },
  },
}

function LinkButton({ link, theme }) {
  const sold    = link.type === 'Recently Sold'
  const colors  = sold ? theme.recentlySold : theme.forSale
  const shadow  = `0 5px 0 ${colors.press}, 0 8px 18px rgba(0,0,0,0.55)`
  const shadowSm = `0 2px 0 ${colors.press}, 0 4px 8px rgba(0,0,0,0.4)`

  function press(e)   { e.currentTarget.style.transform = 'translateY(3px)'; e.currentTarget.style.boxShadow = shadowSm }
  function release(e) { e.currentTarget.style.transform = '';               e.currentTarget.style.boxShadow = shadow }

  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex-1 flex items-center justify-between gap-2 px-4 py-3 rounded-lg select-none transition-[box-shadow,transform] duration-75"
      style={{
        background: `linear-gradient(to bottom, ${colors.from}, ${colors.to})`,
        boxShadow:  shadow,
        border:     '1px solid rgba(255,255,255,0.08)',
      }}
      onMouseDown={press}
      onMouseUp={release}
      onMouseLeave={release}
    >
      <span className={`text-sm font-bold leading-tight ${sold ? 'text-[#FFF97F]' : 'text-white'}`}>
        {link.type}
      </span>
      <span className="text-white/40 text-lg leading-none shrink-0">›</span>
    </a>
  )
}

function SiteGroup({ site }) {
  const theme = SITE_THEME[site.name]
  return (
    <div>
      <p className="text-xs font-semibold mb-2" style={{ color: theme.heading }}>
        {site.name}
      </p>
      <div className="flex gap-2">
        {site.links.map((link, i) => (
          <LinkButton key={i} link={link} theme={theme} />
        ))}
      </div>
    </div>
  )
}

function SuburbSection({ suburb }) {
  return (
    <div className="flex-1 min-w-0 bg-[#111] border border-[#1C1C1C] rounded-xl p-5">
      <div className="mb-5">
        <h3 className="text-2xl font-bold text-white tracking-tight">{suburb.label}</h3>
        <p className="text-sm text-[#555] mt-0.5">
          {suburb.postcode} · {suburb.state} · {suburb.criteria}
        </p>
      </div>
      <div className="flex flex-col gap-4">
        {suburb.sites.map(site => (
          <SiteGroup key={site.name} site={site} />
        ))}
      </div>
    </div>
  )
}

export default function RecentSales() {
  return (
    <section className="mb-8">
      <div className="flex items-center gap-3 mb-4">
        <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
        <h2 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em]">
          Property Search
        </h2>
        <div className="flex-1 h-px bg-[#1C1C1C]" />
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        {SUBURBS.map(s => (
          <SuburbSection key={s.postcode} suburb={s} />
        ))}
      </div>
    </section>
  )
}

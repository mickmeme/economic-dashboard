const SUBURBS = [
  {
    label:    'Point Cook',
    postcode: '3030',
    state:    'VIC',
    criteria: '4–5 bed house · min 4 bath',
    links: [
      {
        site: 'Domain',
        type: 'For Sale',
        url:  'https://www.domain.com.au/sale/point-cook-vic-3030/?bedrooms=4-5&bathrooms=4&property-types=house&view=map',
      },
      {
        site: 'Domain',
        type: 'Recently Sold',
        url:  'https://www.domain.com.au/sold-listings/point-cook-vic-3030/?bedrooms=4-5&bathrooms=4&property-types=house&view=map',
      },
      {
        site: 'REA',
        type: 'For Sale',
        url:  'https://www.realestate.com.au/buy/property-house-in-point+cook,+vic+3030/map-1?numBeds=4&numBaths=4',
      },
      {
        site: 'REA',
        type: 'Recently Sold',
        url:  'https://www.realestate.com.au/sold/property-house-in-point+cook,+vic+3030/map-1?numBeds=4&numBaths=4',
      },
    ],
  },
  {
    label:    'Varsity Lakes',
    postcode: '4227',
    state:    'QLD',
    criteria: '3 bed townhouse · min 2 bath',
    links: [
      {
        site: 'Domain',
        type: 'For Sale',
        url:  'https://www.domain.com.au/sale/varsity-lakes-qld-4227/?bedrooms=3&bathrooms=2&property-types=townhouse&view=map',
      },
      {
        site: 'Domain',
        type: 'Recently Sold',
        url:  'https://www.domain.com.au/sold-listings/varsity-lakes-qld-4227/?bedrooms=3&bathrooms=2&property-types=townhouse&view=map',
      },
      {
        site: 'REA',
        type: 'For Sale',
        url:  'https://www.realestate.com.au/buy/property-townhouse-in-varsity+lakes,+qld+4227/map-1?numBeds=3&numBaths=2',
      },
      {
        site: 'REA',
        type: 'Recently Sold',
        url:  'https://www.realestate.com.au/sold/property-townhouse-in-varsity+lakes,+qld+4227/map-1?numBeds=3&numBaths=2',
      },
    ],
  },
]

const BTN_STYLES = {
  'Domain-For Sale': {
    gradient: 'linear-gradient(to bottom, #2563eb, #1d4ed8)',
    shadow:   '0 5px 0 #1e3a8a, 0 8px 16px rgba(0,0,0,0.45)',
    shadowSm: '0 2px 0 #1e3a8a, 0 4px 8px rgba(0,0,0,0.3)',
    labelColor: '#93c5fd',
  },
  'Domain-Recently Sold': {
    gradient: 'linear-gradient(to bottom, #1d4ed8, #1e40af)',
    shadow:   '0 5px 0 #1e3a8a, 0 8px 16px rgba(0,0,0,0.45)',
    shadowSm: '0 2px 0 #1e3a8a, 0 4px 8px rgba(0,0,0,0.3)',
    labelColor: '#93c5fd',
  },
  'REA-For Sale': {
    gradient: 'linear-gradient(to bottom, #dc2626, #b91c1c)',
    shadow:   '0 5px 0 #7f1d1d, 0 8px 16px rgba(0,0,0,0.45)',
    shadowSm: '0 2px 0 #7f1d1d, 0 4px 8px rgba(0,0,0,0.3)',
    labelColor: '#fca5a5',
  },
  'REA-Recently Sold': {
    gradient: 'linear-gradient(to bottom, #b91c1c, #991b1b)',
    shadow:   '0 5px 0 #7f1d1d, 0 8px 16px rgba(0,0,0,0.45)',
    shadowSm: '0 2px 0 #7f1d1d, 0 4px 8px rgba(0,0,0,0.3)',
    labelColor: '#fca5a5',
  },
}

function LinkButton({ link }) {
  const key    = `${link.site}-${link.type}`
  const styles = BTN_STYLES[key]
  const sold   = link.type === 'Recently Sold'

  function press(e) {
    e.currentTarget.style.transform = 'translateY(3px)'
    e.currentTarget.style.boxShadow = styles.shadowSm
  }
  function release(e) {
    e.currentTarget.style.transform = ''
    e.currentTarget.style.boxShadow = styles.shadow
  }

  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center justify-between gap-3 px-4 py-3 rounded-lg select-none transition-[box-shadow,transform] duration-75"
      style={{
        background: styles.gradient,
        boxShadow:  styles.shadow,
        border:     '1px solid rgba(255,255,255,0.12)',
      }}
      onMouseDown={press}
      onMouseUp={release}
      onMouseLeave={release}
    >
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: styles.labelColor }}>
          {link.site === 'REA' ? 'realestate.com.au' : 'domain.com.au'}
        </span>
        <span className={`text-sm font-bold leading-tight ${sold ? 'text-[#FFF97F]' : 'text-white'}`}>
          {link.type}
        </span>
      </div>
      <span className="text-white/50 text-lg shrink-0 leading-none">›</span>
    </a>
  )
}

function SuburbSection({ suburb }) {
  return (
    <div className="flex-1 min-w-0 bg-[#111] border border-[#1C1C1C] rounded-xl p-5">
      <div className="mb-4">
        <h3 className="text-2xl font-bold text-white tracking-tight">{suburb.label}</h3>
        <p className="text-sm text-[#555] mt-0.5">
          {suburb.postcode} · {suburb.state} · {suburb.criteria}
        </p>
      </div>
      <div className="flex flex-col gap-2.5">
        {suburb.links.map((link, i) => (
          <LinkButton key={i} link={link} />
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

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

const SITE_BG = {
  Domain: { base: '#1e3a5f', hover: '#1e4a7a' },
  REA:    { base: '#5f1e1e', hover: '#7a1e1e' },
}

const SITE_LABEL_COLOR = {
  Domain: '#93c5fd',
  REA:    '#fca5a5',
}

function LinkButton({ link }) {
  const sold = link.type === 'Recently Sold'
  const bg   = SITE_BG[link.site]
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center justify-between gap-3 px-4 py-3 rounded-md font-medium text-sm transition-colors"
      style={{ backgroundColor: bg.base }}
      onMouseEnter={e => { e.currentTarget.style.backgroundColor = bg.hover }}
      onMouseLeave={e => { e.currentTarget.style.backgroundColor = bg.base }}
    >
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="text-[9px] font-semibold uppercase tracking-widest" style={{ color: SITE_LABEL_COLOR[link.site] }}>
          {link.site === 'REA' ? 'realestate.com.au' : 'domain.com.au'}
        </span>
        <span className={`text-[13px] font-semibold leading-tight ${sold ? 'text-[#FFF97F]' : 'text-green-300'}`}>
          {link.type}
        </span>
      </div>
      <span className="text-white/40 text-base shrink-0">→</span>
    </a>
  )
}

function SuburbSection({ suburb }) {
  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 mb-1">
        <span className="w-0.5 h-4 bg-[#FFF97F] shrink-0" />
        <h3 className="text-[10px] font-bold text-[#666] uppercase tracking-[0.2em]">
          {suburb.label}
          <span className="text-[#333] ml-1.5">{suburb.postcode}</span>
        </h3>
      </div>
      <p className="text-[9px] text-[#444] uppercase tracking-wider mb-3 ml-2.5">
        {suburb.criteria}
      </p>
      <div className="flex flex-col gap-2">
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

      <div className="flex flex-col sm:flex-row gap-6">
        {SUBURBS.map(s => (
          <SuburbSection key={s.postcode} suburb={s} />
        ))}
      </div>
    </section>
  )
}

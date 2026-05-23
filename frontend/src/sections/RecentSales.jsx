const SUBURBS = [
  {
    label:    'Point Cook',
    postcode: '3030',
    state:    'VIC',
    criteria: '4–5 bed house · min 4 bath',
    links: [
      {
        site:  'Domain',
        type:  'For Sale',
        url:   'https://www.domain.com.au/sale/point-cook-vic-3030/?bedrooms=4-5&bathrooms=4&property-types=house',
      },
      {
        site:  'Domain',
        type:  'Recently Sold',
        url:   'https://www.domain.com.au/sold-listings/point-cook-vic-3030/?bedrooms=4-5&bathrooms=4&property-types=house',
      },
      {
        site:  'REA',
        type:  'For Sale',
        url:   'https://www.realestate.com.au/buy/property-house-in-point+cook,+vic+3030/list-1?numBeds=4&numBaths=4',
      },
      {
        site:  'REA',
        type:  'Recently Sold',
        url:   'https://www.realestate.com.au/sold/property-house-in-point+cook,+vic+3030/list-1?numBeds=4&numBaths=4',
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
        site:  'Domain',
        type:  'For Sale',
        url:   'https://www.domain.com.au/sale/varsity-lakes-qld-4227/?bedrooms=3&bathrooms=2&property-types=townhouse',
      },
      {
        site:  'Domain',
        type:  'Recently Sold',
        url:   'https://www.domain.com.au/sold-listings/varsity-lakes-qld-4227/?bedrooms=3&bathrooms=2&property-types=townhouse',
      },
      {
        site:  'REA',
        type:  'For Sale',
        url:   'https://www.realestate.com.au/buy/property-townhouse-in-varsity+lakes,+qld+4227/list-1?numBeds=3&numBaths=2',
      },
      {
        site:  'REA',
        type:  'Recently Sold',
        url:   'https://www.realestate.com.au/sold/property-townhouse-in-varsity+lakes,+qld+4227/list-1?numBeds=3&numBaths=2',
      },
    ],
  },
]

const SITE_COLORS = {
  Domain: '#60a5fa',
  REA:    '#f87171',
}

function LinkCard({ link }) {
  const sold = link.type === 'Recently Sold'
  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className="bg-[#0D0D0D] border border-[#1C1C1C] rounded p-3 flex flex-col gap-1.5 hover:border-[#2A2A2A] hover:bg-[#111] transition-colors group"
    >
      <span
        className="text-[9px] font-bold uppercase tracking-widest"
        style={{ color: SITE_COLORS[link.site] }}
      >
        {link.site === 'REA' ? 'realestate.com.au' : 'domain.com.au'}
      </span>
      <span className={`text-[11px] font-semibold ${sold ? 'text-[#FFF97F]' : 'text-green-400'}`}>
        {link.type}
      </span>
      <span className="text-[10px] text-[#444] group-hover:text-[#666] transition-colors mt-1">
        View listings →
      </span>
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
      <div className="grid grid-cols-2 gap-2">
        {suburb.links.map((link, i) => (
          <LinkCard key={i} link={link} />
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

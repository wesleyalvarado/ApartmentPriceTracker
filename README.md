# Apartment Price Tracker

A personal price tracking dashboard for Dallas, TX. Tracks apartment pricing and house market data, stores historical data in SQLite, and surfaces it through a two-tab Angular dashboard.

Currently tracking apartments at:
- **Camden Greenville** — Uptown Dallas
- **SkyHouse Dallas** — Victory Park

House prices tracked for zip codes: **75206** (M Streets), **75214** (Lakewood), **75238** (Lake Highlands)

---

## What It Does

### Apartments tab
- Scrapes per-unit pricing and availability dates for all floor plans
- Tracks lease-term pricing (4, 5, 6, and 14 month terms) via each complex's GraphQL API
- Detects rented units by comparing the current scrape against prior snapshots
- Shows a price history chart per floor plan as data accumulates over time
- Displays floor plan layout images in the expanded card view
- Links directly to each floor plan's listing page on the complex's website
- Shows a price change badge per card — red for drops (primary signal), orange for increases (anomaly flag)
- Card price and availability date are always paired to the same cheapest unit

### House Prices tab
- ZHVI median home value trend chart by zip code (Zillow, 3 home types)
- Latest Redfin market metrics table — list/sale price, inventory, days on market, sale-to-list ratio
- Affordability calculator — max purchase price given monthly budget, rate, and down payment

---

## Stack

| Layer | Technology |
|-------|-----------|
| Scraper | Python · `requests` · `BeautifulSoup` · GraphQL |
| Database | SQLite (`data/apartments.db`) |
| Backend | FastAPI · Python · raw SQL via `sqlite3` stdlib |
| Frontend | Angular 20 · PrimeNG v20 · Tailwind v4 · Chart.js |
| Tests | Jasmine · Karma (58 tests) |

---

## Project Structure

```
AptPricing/
├── data/
│   └── apartments.db          # SQLite database (apartments + house prices)
├── scraper/
│   ├── camden_greenville/
│   │   ├── scraper.py            # Main scraper (floor plans + per-unit prices)
│   │   ├── lease_terms.py        # Per-lease-term pricing via GraphQL
│   │   └── parser.py             # __NEXT_DATA__ JSON parser
│   ├── skyhouse_dallas/
│   │   ├── scraper.py            # SkyHouse scraper (Yardi/RentCafe)
│   │   └── lease_terms.py        # SkyHouse lease term pricing
│   └── house_prices/
│       ├── migrate.py            # Creates ZHVI/Redfin tables; seeds zip metadata
│       ├── ingest_zhvi.py        # Downloads Zillow ZHVI CSV (run monthly)
│       └── ingest_redfin.py      # Streams Redfin weekly data ~500 MB (run weekly)
├── api/
│   └── main.py                   # FastAPI app — all endpoints
└── frontend/
    └── src/app/
        ├── app.ts                # Root — nav tabs + router-outlet
        ├── app.config.ts         # Router, HttpClient, PrimeNG config
        ├── app.routes.ts         # / → Apartments, /house-prices → House Prices
        ├── models/               # Shared TypeScript interfaces
        ├── services/             # ApiService + DashboardStateService
        └── components/
            ├── dashboard/        # Apartments page — owns all signals and state
            ├── house-prices/     # House Prices page — ZHVI chart, Redfin table, calculator
            ├── filter-bar/       # Stateless filter panel (5 filters, all @Input/@Output)
            ├── floor-plan-card/  # Stateless card + expanded unit table + chart
            ├── price-drop-badge/ # Price change badge (red drop / orange increase)
            └── floor-plan-link/  # External link component (Camden slug, SkyHouse fixed URL)
```

---

## Running Locally

```bash
# 1. Start the API
cd api && uvicorn main:app --reload
# http://localhost:8000

# 2. Start the frontend
cd frontend && ng serve
# http://localhost:4200
```

---

## Data Refresh

### Apartment pricing — run on demand or schedule daily

```bash
cd scraper/camden_greenville && python scraper.py       # base pricing
cd scraper/camden_greenville && python lease_terms.py  # lease-term pricing (run after scraper.py)
cd scraper/skyhouse_dallas && python scraper.py
cd scraper/skyhouse_dallas && python lease_terms.py
```

### House price data

| Data | Cadence | Command |
|------|---------|---------|
| Zillow ZHVI | **Monthly** — after the 15th when Zillow publishes new estimates | `python scraper/house_prices/ingest_zhvi.py --all-types` |
| Redfin weekly | **Weekly** — Redfin updates every Monday (~500 MB download) | `python scraper/house_prices/ingest_redfin.py` |

---

## API Endpoints

### Apartments

| Endpoint | Description |
|----------|-------------|
| `GET /api/complexes` | All tracked complexes |
| `GET /api/lease_terms[?complex_id=N]` | Available lease term months |
| `GET /api/floorplans[?complex_id=N][?lease_term=N]` | Floor plan summaries; min price and availability date paired to the cheapest unit |
| `GET /api/units/{floorplan_name}[?complex_id=N][?lease_term=N]` | Units for a floor plan |
| `GET /api/price-drops[?complex_id=N][?lease_term=N]` | Per-floor-plan greatest price change since first recorded; drops take priority over increases |
| `GET /api/rented[?complex_id=N][?days=14]` | Units absent from the latest scrape |
| `GET /api/history/floorplan/{name}?days=60` | Min price trend for charting |
| `GET /api/history/{unit_id}?days=30` | Price history for a specific unit |
| `GET /api/stats[?complex_id=N]` | All-time min/max vs current per floor plan |
| `GET /api/alerts?max_price=&bedrooms=` | Units at or below a price threshold |
| `GET /health` | Liveness check |

### House Prices

| Endpoint | Description |
|----------|-------------|
| `GET /api/house-prices/summary` | Latest ZHVI + Redfin snapshot per zip |
| `GET /api/house-prices/zhvi?home_type=&months=` | Monthly ZHVI trend for charting |
| `GET /api/house-prices/redfin?months=` | Weekly Redfin data |

---

## Dashboard Features

### Apartments
- **Filters** — Complex, bedrooms, lease term, availability window, available/rented/all status
- **Stats bar** — Live unit count, starting price, floor plan count — all react to active filters
- **Cards sorted by price** — Lowest `display_min` first; re-sorts on every filter change
- **Price + date consistency** — The displayed price and availability date always correspond to the same cheapest unit
- **Price change badge** — Red pill for drops (primary signal), orange pill for increases (anomaly); reflects the active lease term; tooltip shows the specific unit, original price, and date first seen. Short-term badges (4/5/6 mo) can be noisy due to Camden's dynamic premium rotation — the 14-month badge is the most reliable signal
- **Expanded card** — Price history chart, floor plan layout image, unit table with rented units shown inline
- **Direct links** — Each card links to the floor plan's listing page

### House Prices
- **ZHVI trend chart** — Multi-line Chart.js chart across 3 zips; filter by home type (All / 3BR / SFR) and history window (12–60 months)
- **Stats bar** — Current median home value per zip with days-on-market and inventory when available
- **Redfin metrics table** — Latest week's list price, sale price, inventory, new listings, days on market, sale-to-list ratio across all 3 zips
- **Affordability calculator** — Enter monthly budget, mortgage rate, and down payment; outputs max purchase price, P&I, tax, insurance breakdown

---

## Running Tests

```bash
cd frontend && ng test --watch=false --browsers=ChromeHeadless
```

58 tests across: `ApiService`, `DashboardStateService`, `DashboardComponent`, `FilterBarComponent`, `FloorPlanCardComponent`, `FloorPlanLinkComponent`.

---

## What's Next

- **Scheduling** — macOS launchd: apartments daily, ZHVI monthly, Redfin weekly
- **Price alerts** — Notify when a unit drops below a target price (`price_alerts` table already exists)
- **More complexes** — Add a new scraper in `scraper/<slug>/` and the frontend picks it up automatically

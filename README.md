# Apartment Price Tracker

A personal apartment price tracking dashboard for Dallas, TX. Scrapes floor plan and unit pricing from apartment complex websites on a schedule, stores historical data in SQLite, and surfaces it through a filterable Angular dashboard.

Currently tracking:
- **Camden Greenville** — Uptown Dallas
- **SkyHouse Dallas** — Victory Park

---

## What It Does

- Scrapes per-unit pricing and availability dates for all floor plans
- Tracks lease-term pricing (4, 5, 6, and 14 month terms) via each complex's GraphQL API
- Detects rented units by comparing the current scrape against prior snapshots
- Shows a price history chart per floor plan as data accumulates over time (all lease terms)
- Displays floor plan layout images in the expanded card view
- Links directly to each floor plan's listing page on the complex's website
- Shows a price change badge per card — red for drops (primary signal), orange for increases (anomaly flag)
- Card price and availability date are always paired to the same cheapest unit

---

## Stack

| Layer | Technology |
|-------|-----------|
| Scraper | Python · `requests` · `BeautifulSoup` · GraphQL |
| Database | SQLite (`data/camden_prices.db`) |
| Backend | FastAPI · Python · raw SQL via `sqlite3` stdlib |
| Frontend | Angular 20 · PrimeNG v20 · Tailwind v4 · Chart.js |
| Tests | Jasmine · Karma (58 tests) |

---

## Project Structure

```
AptPricing/
├── data/
│   └── camden_prices.db          # SQLite database
├── scraper/
│   ├── camden_greenville/
│   │   ├── scraper.py            # Main scraper (floor plans + per-unit prices)
│   │   ├── lease_terms.py        # Per-lease-term pricing via GraphQL
│   │   └── parser.py             # __NEXT_DATA__ JSON parser
│   └── skyhouse_dallas/
│       ├── scraper.py            # SkyHouse scraper (Yardi/RentCafe)
│       └── lease_terms.py        # SkyHouse lease term pricing
├── api/
│   └── main.py                   # FastAPI app — all endpoints
└── frontend/
    └── src/app/
        ├── models/               # Shared TypeScript interfaces
        ├── services/             # ApiService + DashboardStateService
        └── components/
            ├── dashboard/        # Page component — owns all signals and state
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

# 3. Refresh pricing data
cd scraper/camden_greenville && python scraper.py       # base pricing
cd scraper/camden_greenville && python lease_terms.py  # lease-term pricing
cd scraper/skyhouse_dallas && python scraper.py
cd scraper/skyhouse_dallas && python lease_terms.py
```

---

## API Endpoints

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

---

## Dashboard Features

- **Filters** — Complex, bedrooms, lease term, availability window, available/rented/all status
- **Stats bar** — Live unit count, starting price, floor plan count, and available bedroom types — all react to active filters
- **Cards sorted by price** — Lowest `display_min` first; re-sorts on every filter change
- **Price + date consistency** — The displayed price and availability date always correspond to the same cheapest unit in the floor plan
- **Price change badge** — Red pill for drops (primary signal), orange pill for increases (anomaly); reflects the active lease term; tooltip shows the specific unit, original price, and date first seen. Short-term badges (4/5/6 mo) can be noisy due to Camden's dynamic premium rotation — the 14-month badge is the most reliable signal
- **Expanded card** — Price history chart (all lease terms), floor plan layout image, unit table with rented units shown inline
- **Direct links** — Each card links to the floor plan's listing page (Camden: per-slug with `?floor=N`; SkyHouse: fixed floor plans page)

---

## Running Tests

```bash
cd frontend && ng test --watch=false --browsers=ChromeHeadless
```

58 tests across: `ApiService`, `DashboardStateService`, `DashboardComponent`, `FilterBarComponent`, `FloorPlanCardComponent`, `FloorPlanLinkComponent`.

---

## What's Next

- **Scheduling** — macOS launchd to run scrapers on a daily/weekly cadence
- **Favorites** — Star floor plans to surface them quickly
- **Price alerts** — Notify when a unit drops below a target price (`price_alerts` table already exists)
- **More complexes** — Add a new scraper in `scraper/<slug>/` and the frontend picks it up automatically

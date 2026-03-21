# Frontend

Angular 20 dashboard for the Apartment Price Tracker. See the [root README](../README.md) for full project context.

## Stack

- Angular 20 (standalone components, signals, inline templates)
- PrimeNG v20 (UI components)
- Tailwind v4 (utility styles)
- Chart.js via `p-chart` (price history)
- Jasmine / Karma (unit tests)

## Development

```bash
npm install
ng serve        # http://localhost:4200 — requires API running on :8000
ng test --watch=false --browsers=ChromeHeadless
ng build
```

## Structure

```
src/app/
├── models/
│   └── apartment.model.ts         # All shared interfaces and option types
├── services/
│   ├── api.service.ts             # HttpClient wrapper for all backend calls
│   └── dashboard-state.service.ts # Shared formatting helpers (bedroomLabel, formatDate)
└── components/
    ├── dashboard/                 # Page component — signals, computed, actions
    ├── filter-bar/                # Stateless filter panel (12 @Inputs, 5 @Outputs)
    ├── floor-plan-card/           # Stateless card + expanded unit table + chart
    └── floor-plan-link/           # External link (Camden slug-based, SkyHouse fixed)
```

All component templates are inlined in the `.ts` file — no separate `.html` files.

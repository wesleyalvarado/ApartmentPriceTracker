# Frontend

Angular 20 dashboard for the Apartment Price Tracker. See the [root README](../README.md) for full project context.

## Stack

- Angular 20 (standalone components, signals, inline templates)
- PrimeNG v20 (UI components)
- Tailwind v4 (utility styles)
- Chart.js via `p-chart` (price history)
- Jasmine / Karma (unit tests)

## Development

The API base URL is configured in `src/environments/environment.ts`. It currently points to the Java backend on port **8001**.

```bash
npm install
ng serve        # http://localhost:4200 — requires Java backend running on :8001
ng test --watch=false --browsers=ChromeHeadless
ng build                         # dev build
ng build --configuration=production  # prod build (swaps in environment.prod.ts)
```

To switch to the FastAPI backend, change `apiBase` in `src/environments/environment.ts` to `http://localhost:8000/api` and restart `ng serve`.

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

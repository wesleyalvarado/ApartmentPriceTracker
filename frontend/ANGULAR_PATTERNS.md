# Angular Component Patterns — AptPricing

All components are **standalone** with **inline template and styles** (no separate `.html` or `.scss` files).

---

## File Structure

```
frontend/src/
├── app/
│   ├── components/
│   │   └── <component-name>/
│   │       ├── <component-name>.component.ts   ← template + styles inline here
│   │       └── <component-name>.component.spec.ts
│   ├── models/
│   │   └── apartment.model.ts                  ← all interfaces/types
│   ├── services/
│   │   ├── api.service.ts
│   │   └── dashboard-state.service.ts
│   ├── app.ts                                  ← root component + nav
│   ├── app.config.ts                           ← providers + PrimeNG theme
│   └── app.routes.ts
├── styles.css                                  ← Tailwind v4 + PrimeNG overrides (NOT .scss)
├── index.html
└── main.ts
```

---

## Component Template

```typescript
import { Component, input, output, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-example',
  standalone: true,
  imports: [CommonModule],
  styles: [`
    /* component-scoped CSS here */
    .container { display: flex; }
  `],
  template: `
    <div class="container">
      <p>{{ label() }}</p>
    </div>
  `
})
export class ExampleComponent {
  // Inputs (required)
  label = input.required<string>();

  // Inputs (optional with default)
  count = input<number>(0);

  // Outputs
  clicked = output<string>();

  // Local state
  loading = signal(false);

  // Derived state
  display = computed(() => `${this.label()} (${this.count()})`);
}
```

---

## Signals Pattern

| Pattern | Usage |
|---------|-------|
| `signal(value)` | Local mutable state |
| `input<T>()` | Optional input with type |
| `input.required<T>()` | Required input |
| `output<T>()` | Typed event emitter |
| `computed(() => ...)` | Derived from signals, auto-tracks deps |

**No `@Input()` / `@Output()` decorators** — use `input()` / `output()` functions only.

---

## PrimeNG Usage

Import modules directly in the component's `imports` array:

```typescript
imports: [
  CommonModule,
  CardModule,       // p-card
  TableModule,      // p-table
  TagModule,        // p-tag
  SkeletonModule,   // p-skeleton
  ChartModule,      // p-chart
  TooltipModule,    // pTooltip directive
  SelectButtonModule,
]
```

---

## Styling Rules

- **Tailwind v4** via `@import "tailwindcss"` in `styles.css` — utility classes available globally
- **Inline `styles`** array on the component for component-scoped CSS
- **No `.scss` files** — `styles.css` is plain CSS (Sass deprecation issue with Tailwind v4)
- PrimeNG theme overrides go in `styles.css` under `@layer primeng { ... }`
- Brand colors defined as CSS custom properties in `styles.css`:
  ```css
  --color-camden-green: #2B5741;
  --color-camden-light: #3E7A5A;
  --color-camden-pale:  #EAF2ED;
  --color-camden-gold:  #C8A84B;
  ```

---

## Models (apartment.model.ts)

All interfaces/types live in one file. Add new interfaces there — no per-feature model files.

Key types:
- `FloorPlan`, `Unit`, `DisplayFloorPlan`, `DisplayUnit`
- `PriceDrop`, `RentedUnit`, `PricePoint`, `Stats`
- `Complex`, `HousePriceSummary`, `ZhviPoint`, `RedfinPoint`
- Option types: `BedroomOption`, `LeaseTermOption`, `ComplexOption`, `StatusOption`, `SortOption`
- Type aliases: `StatusValue`, `SortValue`

---

## ApiService

Base URL: `http://localhost:8000/api`

- All methods return `Observable<T>` via `HttpClient`
- `lease_term` param is **omitted** when value is `15` (default/any)
- Add new endpoints as methods on the existing service — no new service files

---

## Routing

```typescript
// app.routes.ts
[
  { path: '',             component: DashboardComponent },
  { path: 'house-prices', component: HousePricesComponent },
  { path: '**',           redirectTo: '' },
]
```

New pages: add route here + nav link in `app.ts`.

---

## Adding a New Component

1. Create `frontend/src/app/components/<name>/<name>.component.ts`
2. Use standalone + inline template/styles (see template above)
3. Add interfaces to `apartment.model.ts`
4. Add API methods to `api.service.ts`
5. Add route to `app.routes.ts` and nav link to `app.ts` if it's a page

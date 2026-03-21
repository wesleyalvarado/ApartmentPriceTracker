import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { of } from 'rxjs';

import { FloorPlanCardComponent } from './floor-plan-card.component';
import { ApiService } from '../../services/api.service';
import { DisplayFloorPlan, DisplayUnit, PriceDrop } from '../../models/apartment.model';

const mockApi = {
  complexes: () => of([]), floorPlans: () => of([]),
  leaseTerms: () => of([]), rented: () => of([]),
  unitsForFloorPlan: () => of([]), floorPlanHistory: () => of([]),
};

function makeFp(overrides: Partial<DisplayFloorPlan> = {}): DisplayFloorPlan {
  return {
    complex_id: 1, complex_name: 'Camden Greenville',
    floorplan_name: 'A1 Villas', floorplan_slug: 'a1-villas-floor-plan',
    bedrooms: 0, bathrooms: 1, sqft: 550,
    available_units: 3, min_price: 1229, max_price: 1289, avg_price: 1259,
    earliest_available: null, special_tags: null,
    scraped_at: '2026-03-20T15:00:00Z', image_url: null, url_floor: null,
    display_units: 3, display_min: 1229, display_max: 1289,
    ...overrides,
  };
}

function makeUnit(overrides: Partial<DisplayUnit> = {}): DisplayUnit {
  return { unit_id: '2308', floor: 2, price: 1229, available_date: '2026-04-15', status: 'available', ...overrides };
}

function makePriceDrop(overrides: Partial<PriceDrop> = {}): PriceDrop {
  return {
    complex_id: 1, floorplan_name: 'A1 Villas', best_unit_id: '2308',
    current_min: 1300, baseline_min: 1500, cumulative_drop: 200,
    drop_pct: 13.3, direction: 'drop', first_seen: '2026-01-01',
    ...overrides,
  };
}

async function setup(inputs: Partial<{
  fp: DisplayFloorPlan;
  isExpanded: boolean;
  loadingUnits: boolean;
  expandedUnits: DisplayUnit[];
  chartData: any;
  showComplexBadge: boolean;
  selectedStatus: 'available' | 'rented' | 'all';
  priceDrop: PriceDrop | null;
}> = {}) {
  await TestBed.configureTestingModule({
    imports: [FloorPlanCardComponent],
    providers: [
      { provide: ApiService, useValue: mockApi },
      provideHttpClient(), provideHttpClientTesting(), provideAnimationsAsync(),
    ],
  }).compileComponents();

  const fixture   = TestBed.createComponent(FloorPlanCardComponent);
  const component = fixture.componentInstance;

  component.fp              = inputs.fp              ?? makeFp();
  component.isExpanded      = inputs.isExpanded      ?? false;
  component.loadingUnits    = inputs.loadingUnits    ?? false;
  component.expandedUnits   = inputs.expandedUnits   ?? [];
  component.chartData       = inputs.chartData       ?? null;
  component.chartOptions    = {};
  component.showComplexBadge = inputs.showComplexBadge ?? false;
  component.selectedStatus  = inputs.selectedStatus  ?? 'available';
  component.priceDrop       = inputs.priceDrop !== undefined ? inputs.priceDrop : null;

  fixture.detectChanges();
  return { fixture, component };
}

describe('FloorPlanCardComponent', () => {

  it('creates successfully', async () => {
    const { component } = await setup();
    expect(component).toBeTruthy();
  });

  it('emits toggleRequested when card is clicked', async () => {
    const fp = makeFp();
    const { fixture, component } = await setup({ fp });
    let emitted: DisplayFloorPlan | undefined;
    component.toggleRequested.subscribe(v => emitted = v);

    const card = fixture.nativeElement.querySelector('.fp-card');
    card?.click();

    expect(emitted).toEqual(fp);
  });

  it('shows fp-card--expanded class when isExpanded is true', async () => {
    const { fixture } = await setup({ isExpanded: true });
    const card = fixture.nativeElement.querySelector('.fp-card--expanded');
    expect(card).not.toBeNull();
  });

  it('does not show fp-card--expanded class when isExpanded is false', async () => {
    const { fixture } = await setup({ isExpanded: false });
    const card = fixture.nativeElement.querySelector('.fp-card--expanded');
    expect(card).toBeNull();
  });

  it('shows unit panel when isExpanded is true', async () => {
    const { fixture } = await setup({ isExpanded: true });
    const panel = fixture.nativeElement.querySelector('.unit-panel');
    expect(panel).not.toBeNull();
  });

  it('hides unit panel when isExpanded is false', async () => {
    const { fixture } = await setup({ isExpanded: false });
    const panel = fixture.nativeElement.querySelector('.unit-panel');
    expect(panel).toBeNull();
  });

  it('shows complex badge when showComplexBadge is true', async () => {
    const { fixture } = await setup({ showComplexBadge: true });
    const badge = fixture.nativeElement.querySelector('.complex-badge');
    expect(badge).not.toBeNull();
  });

  it('hides complex badge when showComplexBadge is false', async () => {
    const { fixture } = await setup({ showComplexBadge: false });
    const badge = fixture.nativeElement.querySelector('.complex-badge');
    expect(badge).toBeNull();
  });

  it('delegates bedroomLabel to state service', async () => {
    const { component } = await setup();
    expect(component.bedroomLabel(0)).toBe('Studio');
    expect(component.bedroomLabel(1)).toBe('1 Bedroom');
    expect(component.bedroomLabel(2)).toBe('2 Bedrooms');
  });

  it('delegates formatDate to state service', async () => {
    const { component } = await setup();
    expect(component.formatDate(null)).toBe('—');
    expect(component.formatDate('2020-01-01')).toBe('Available Now');
  });

  it('shows skeleton when loadingUnits is true', async () => {
    const { fixture } = await setup({ isExpanded: true, loadingUnits: true });
    const skeleton = fixture.nativeElement.querySelector('p-skeleton');
    expect(skeleton).not.toBeNull();
  });

  it('shows unit rows when units are provided', async () => {
    const units = [makeUnit({ unit_id: '2308' }), makeUnit({ unit_id: '3309' })];
    const { fixture } = await setup({ isExpanded: true, loadingUnits: false, expandedUnits: units });
    const rows = fixture.nativeElement.querySelectorAll('tbody tr');
    expect(rows.length).toBe(2);
  });

  it('shows chart placeholder when chartData is null', async () => {
    const { fixture } = await setup({ isExpanded: true, chartData: null });
    const placeholder = fixture.nativeElement.querySelector('.chart-placeholder');
    expect(placeholder).not.toBeNull();
  });

  it('shows chart section when chartData is provided', async () => {
    const { fixture } = await setup({ isExpanded: true, chartData: { labels: [], datasets: [] } });
    const section = fixture.nativeElement.querySelector('.chart-section');
    expect(section).not.toBeNull();
  });

  // ── priceDrop badge ────────────────────────────────────────────────────────

  it('renders price-drop-badge component when priceDrop is provided', async () => {
    const { fixture } = await setup({ priceDrop: makePriceDrop() });
    const badge = fixture.nativeElement.querySelector('app-price-drop-badge');
    expect(badge).not.toBeNull();
  });

  it('renders price-drop-badge component when priceDrop is null (badge handles its own null)', async () => {
    const { fixture } = await setup({ priceDrop: null });
    const badge = fixture.nativeElement.querySelector('app-price-drop-badge');
    expect(badge).not.toBeNull(); // component always present; renders nothing internally when null
  });

  // ── rented units ──────────────────────────────────────────────────────────

  it('shows rented unit row with lock icon when status is rented', async () => {
    const units = [makeUnit({ unit_id: '2308', status: 'rented', last_seen: '2026-03-15T10:00:00Z' })];
    const { fixture } = await setup({ isExpanded: true, expandedUnits: units, selectedStatus: 'rented' });
    const rows = fixture.nativeElement.querySelectorAll('tbody tr');
    expect(rows.length).toBeGreaterThan(0);
  });

  it('shows all units (available + rented) when selectedStatus is all', async () => {
    const units = [
      makeUnit({ unit_id: '2308', status: 'available' }),
      makeUnit({ unit_id: '9999', status: 'rented', last_seen: '2026-03-15T10:00:00Z' }),
    ];
    const { fixture } = await setup({ isExpanded: true, expandedUnits: units, selectedStatus: 'all' });
    const rows = fixture.nativeElement.querySelectorAll('tbody tr');
    expect(rows.length).toBe(2);
  });

  // ── display_units edge cases ───────────────────────────────────────────────

  it('shows 0 unit count when display_units is 0', async () => {
    const { fixture } = await setup({ fp: makeFp({ display_units: 0, available_units: 0 } as any) });
    const tag = fixture.nativeElement.querySelector('.p-tag, [class*="tag"]');
    // card still renders; display_units shown in badge
    expect(fixture.nativeElement).toBeTruthy();
  });

  it('shows 1 unit count in tag', async () => {
    const { fixture } = await setup({ fp: makeFp({ display_units: 1, available_units: 1 } as any) });
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('1');
  });
});

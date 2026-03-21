import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { of } from 'rxjs';

import { DashboardComponent } from './dashboard.component';
import { ApiService } from '../../services/api.service';
import { FloorPlan, RentedUnit, PriceDrop } from '../../models/apartment.model';

const mockApi = {
  complexes:         () => of([]),
  floorPlans:        () => of([]),
  leaseTerms:        () => of([14, 6, 5, 4]),
  rented:            () => of([]),
  priceDrops:        () => of([]),
  unitsForFloorPlan: () => of([]),
  floorPlanHistory:  () => of([]),
};

function makeFp(overrides: Partial<FloorPlan> = {}): FloorPlan {
  return {
    complex_id: 1, complex_name: 'Camden Greenville',
    floorplan_name: 'A1 Villas', floorplan_slug: 'a1-villas',
    bedrooms: 1, bathrooms: 1, sqft: 600,
    available_units: 2, min_price: 1400, max_price: 1500, avg_price: 1450,
    earliest_available: null, special_tags: null,
    scraped_at: '2026-03-20T10:00:00Z', image_url: null, url_floor: null,
    ...overrides,
  };
}

function makeRented(overrides: Partial<RentedUnit> = {}): RentedUnit {
  return {
    unit_id: '999', floorplan_name: 'A1 Villas', floor: 2,
    bedrooms: 1, last_price: 1350, last_available_date: null,
    last_seen: '2026-03-15T10:00:00Z',
    ...overrides,
  };
}

async function setup() {
  await TestBed.configureTestingModule({
    imports: [DashboardComponent],
    providers: [
      { provide: ApiService, useValue: mockApi },
      provideHttpClient(),
      provideHttpClientTesting(),
      provideAnimationsAsync(),
    ],
  }).compileComponents();

  const fixture   = TestBed.createComponent(DashboardComponent);
  const component = fixture.componentInstance;
  fixture.detectChanges();
  return { fixture, component };
}

describe('DashboardComponent', () => {

  it('creates successfully', async () => {
    const { component } = await setup();
    expect(component).toBeTruthy();
  });

  it('loading is false after ngOnInit', async () => {
    const { component } = await setup();
    expect(component.loading()).toBeFalse();
  });

  // ── planKey ────────────────────────────────────────────────────────────────

  it('planKey returns "complexId:floorplanName"', async () => {
    const { component } = await setup();
    const fp = makeFp({ complex_id: 1, floorplan_name: 'A1 Villas' });
    expect(component.planKey(fp)).toBe('1:A1 Villas');
  });

  it('planKey includes complex_id so different complexes do not collide', async () => {
    const { component } = await setup();
    const fp1 = makeFp({ complex_id: 1, floorplan_name: 'A1' });
    const fp2 = makeFp({ complex_id: 2, floorplan_name: 'A1' });
    expect(component.planKey(fp1)).not.toBe(component.planKey(fp2));
  });

  // ── filtered computed ──────────────────────────────────────────────────────

  it('filtered returns all floor plans when no bedroom filter', async () => {
    const { component } = await setup();
    component.floorPlans.set([makeFp({ bedrooms: 0 }), makeFp({ bedrooms: 1 }), makeFp({ bedrooms: 2 })]);
    expect(component.filtered().length).toBe(3);
  });

  it('filtered narrows by bedroom selection', async () => {
    const { component } = await setup();
    component.floorPlans.set([makeFp({ bedrooms: 1 }), makeFp({ bedrooms: 2 })]);
    component.selectedBedrooms.set(1);
    expect(component.filtered().length).toBe(1);
    expect(component.filtered()[0].bedrooms).toBe(1);
  });

  it('filtered includes Studio (bedrooms=0) when selected', async () => {
    const { component } = await setup();
    component.floorPlans.set([makeFp({ bedrooms: 0 }), makeFp({ bedrooms: 1 })]);
    component.selectedBedrooms.set(0);
    expect(component.filtered().length).toBe(1);
    expect(component.filtered()[0].bedrooms).toBe(0);
  });

  // ── displayFiltered computed ───────────────────────────────────────────────

  it('displayFiltered sorts by display_min ascending', async () => {
    const { component } = await setup();
    component.floorPlans.set([
      makeFp({ floorplan_name: 'B1', min_price: 2000, max_price: 2100 }),
      makeFp({ floorplan_name: 'A1', min_price: 1400, max_price: 1500 }),
    ]);
    const sorted = component.displayFiltered();
    expect(sorted[0].floorplan_name).toBe('A1');
    expect(sorted[1].floorplan_name).toBe('B1');
  });

  it('displayFiltered with status=available uses available_units for display_units', async () => {
    const { component } = await setup();
    component.floorPlans.set([makeFp({ available_units: 3 })]);
    component.selectedStatus.set('available');
    expect(component.displayFiltered()[0].display_units).toBe(3);
  });

  it('displayFiltered with status=rented uses rented unit count', async () => {
    const { component } = await setup();
    component.floorPlans.set([makeFp({ floorplan_name: 'A1 Villas', available_units: 3 })]);
    component.rentedUnits.set([makeRented(), makeRented({ unit_id: '998' })]);
    component.selectedStatus.set('rented');
    const result = component.displayFiltered();
    expect(result.length).toBe(1);
    expect(result[0].display_units).toBe(2);
  });

  it('displayFiltered with status=all combines available and rented', async () => {
    const { component } = await setup();
    component.floorPlans.set([makeFp({ floorplan_name: 'A1 Villas', available_units: 2 })]);
    component.rentedUnits.set([makeRented()]);
    component.selectedStatus.set('all');
    expect(component.displayFiltered()[0].display_units).toBe(3);
  });

  it('displayFiltered excludes floor plans with 0 display_units', async () => {
    const { component } = await setup();
    component.floorPlans.set([makeFp({ available_units: 0 })]);
    component.selectedStatus.set('available');
    expect(component.displayFiltered().length).toBe(0);
  });

  // ── totalUnits / cheapestUnit ──────────────────────────────────────────────

  it('totalUnits sums display_units across all floor plans', async () => {
    const { component } = await setup();
    component.floorPlans.set([
      makeFp({ floorplan_name: 'A1', available_units: 2, min_price: 1400, max_price: 1400 }),
      makeFp({ floorplan_name: 'B1', available_units: 3, min_price: 1600, max_price: 1600 }),
    ]);
    expect(component.totalUnits()).toBe(5);
  });

  it('totalUnits is 0 when no floor plans', async () => {
    const { component } = await setup();
    component.floorPlans.set([]);
    expect(component.totalUnits()).toBe(0);
  });

  it('cheapestUnit returns the floor plan with lowest display_min', async () => {
    const { component } = await setup();
    component.floorPlans.set([
      makeFp({ floorplan_name: 'A1', min_price: 1400, max_price: 1400, available_units: 1 }),
      makeFp({ floorplan_name: 'B1', min_price: 1200, max_price: 1200, available_units: 1 }),
    ]);
    expect(component.cheapestUnit()?.floorplan_name).toBe('B1');
  });

  it('cheapestUnit returns null when no floor plans', async () => {
    const { component } = await setup();
    component.floorPlans.set([]);
    expect(component.cheapestUnit()).toBeNull();
  });

  // ── showComplexBadge / headerSubtitle ──────────────────────────────────────

  it('showComplexBadge is false when only one complex', async () => {
    const { component } = await setup();
    component.complexes.set([{ id: 1, name: 'camden', display_name: 'Camden', city: 'Dallas', state: 'TX', url: null }]);
    expect(component.showComplexBadge()).toBeFalse();
  });

  it('showComplexBadge is true when multiple complexes and no filter selected', async () => {
    const { component } = await setup();
    component.complexes.set([
      { id: 1, name: 'camden', display_name: 'Camden', city: 'Dallas', state: 'TX', url: null },
      { id: 2, name: 'skyhouse', display_name: 'SkyHouse', city: 'Dallas', state: 'TX', url: null },
    ]);
    component.selectedComplexId.set(null);
    expect(component.showComplexBadge()).toBeTrue();
  });

  it('headerSubtitle is "Dallas, TX" when no complex selected', async () => {
    const { component } = await setup();
    component.selectedComplexId.set(null);
    expect(component.headerSubtitle()).toBe('Dallas, TX');
  });

  // ── lease term — all floor plans remain visible ────────────────────────────
  // Regression: previously changing lease term caused some floor plans to
  // disappear because the backend's MAX(scraped_at) per complex excluded units
  // from partial scrape runs. The frontend must pass ALL API-returned plans
  // through displayFiltered as long as available_units > 0.

  it('displayFiltered shows all plans returned by API when all have available_units > 0', async () => {
    const { component } = await setup();
    component.floorPlans.set([
      makeFp({ floorplan_name: 'A1', available_units: 2, min_price: 1400, max_price: 1400 }),
      makeFp({ floorplan_name: 'A2', available_units: 1, min_price: 1500, max_price: 1500 }),
      makeFp({ floorplan_name: 'B1', available_units: 3, min_price: 1800, max_price: 1800 }),
      makeFp({ floorplan_name: 'B2', available_units: 2, min_price: 2000, max_price: 2000 }),
      makeFp({ floorplan_name: 'C1', available_units: 1, min_price: 2200, max_price: 2200 }),
    ]);
    component.selectedStatus.set('available');
    expect(component.displayFiltered().length).toBe(5);
  });

  it('displayFiltered does not apply its own lease-term filter — that is the API\'s job', async () => {
    const { component } = await setup();
    // Simulate what the API returns when lease_term=4 is selected: all plans
    // with data for that term. Frontend must not filter any of them out.
    component.floorPlans.set([
      makeFp({ floorplan_name: 'A2R', available_units: 3, min_price: 1919, max_price: 1919 }),
      makeFp({ floorplan_name: 'A3',  available_units: 2, min_price: 2100, max_price: 2100 }),
    ]);
    component.selectedLeaseTerm.set(4);
    component.selectedStatus.set('available');
    // Both plans should appear regardless of selectedLeaseTerm value on the component
    expect(component.displayFiltered().length).toBe(2);
  });

  it('onLeaseTermChange updates selectedLeaseTerm signal', async () => {
    const { component } = await setup();
    component.onLeaseTermChange(4);
    expect(component.selectedLeaseTerm()).toBe(4);
  });

  it('onLeaseTermChange collapses expanded plan', async () => {
    const { component } = await setup();
    component.expandedPlan.set('1:A1 Villas');
    component.onLeaseTermChange(4);
    expect(component.expandedPlan()).toBeNull();
  });

  it('api.floorPlans is called with the selected lease term', async () => {
    // Verify the API service receives the correct lease_term param by using a spy
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        { provide: ApiService, useValue: mockApi },
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimationsAsync(),
      ],
    }).compileComponents();

    const api = TestBed.inject(ApiService);
    const spy = spyOn(api, 'floorPlans').and.returnValue(of([]));

    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.componentInstance.selectedLeaseTerm.set(4);
    fixture.detectChanges(); // triggers ngOnInit

    // ngOnInit calls _loadFloorPlans which calls floorPlans(selectedLeaseTerm, complexId)
    // Only assert the lease term arg — complexId is null by default which is correct
    expect(spy.calls.mostRecent().args[0]).toBe(4);
  });

  it('displayFiltered still shows all plans after simulated lease term switch', async () => {
    const { component } = await setup();
    // Start on default lease term with 3 plans
    component.floorPlans.set([
      makeFp({ floorplan_name: 'A1', available_units: 2, min_price: 1400, max_price: 1400 }),
      makeFp({ floorplan_name: 'A2', available_units: 1, min_price: 1600, max_price: 1600 }),
      makeFp({ floorplan_name: 'B1', available_units: 3, min_price: 2000, max_price: 2000 }),
    ]);
    expect(component.displayFiltered().length).toBe(3);

    // Simulate API returning the same plans after a lease term switch (as it should)
    component.selectedLeaseTerm.set(4);
    component.floorPlans.set([
      makeFp({ floorplan_name: 'A1', available_units: 2, min_price: 1850, max_price: 1850 }),
      makeFp({ floorplan_name: 'A2', available_units: 1, min_price: 2050, max_price: 2050 }),
      makeFp({ floorplan_name: 'B1', available_units: 3, min_price: 2400, max_price: 2400 }),
    ]);
    // All 3 must still appear — none dropped by frontend filtering
    expect(component.displayFiltered().length).toBe(3);
  });

  // ── priceDropMap ───────────────────────────────────────────────────────────

  it('priceDropMap initializes as empty Map', async () => {
    const { component } = await setup();
    expect(component.priceDropMap().size).toBe(0);
  });

  it('priceDropMap keys are "complexId:floorplanName"', async () => {
    const { component } = await setup();
    const drop: PriceDrop = {
      complex_id: 1, floorplan_name: 'A1 Villas', best_unit_id: '2308',
      current_min: 1300, baseline_min: 1500, cumulative_drop: 200,
      drop_pct: 13.3, direction: 'drop', first_seen: '2026-01-01',
    };
    component.priceDropMap.set(new Map([['1:A1 Villas', drop]]));
    expect(component.priceDropMap().get('1:A1 Villas')).toEqual(drop);
  });
});

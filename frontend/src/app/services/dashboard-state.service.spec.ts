import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';

import { DashboardStateService } from './dashboard-state.service';
import { ApiService } from './api.service';
import { FloorPlan, RentedUnit, Unit } from '../models/apartment.model';

// ── Factories ──────────────────────────────────────────────────────────────

function makeFloorPlan(overrides: Partial<FloorPlan> = {}): FloorPlan {
  return {
    complex_id: 1, complex_name: 'Camden Greenville',
    floorplan_name: 'A1 Villas', floorplan_slug: 'a1-villas-floor-plan',
    bedrooms: 0, bathrooms: 1, sqft: 550,
    available_units: 3, min_price: 1229, max_price: 1289, avg_price: 1259,
    earliest_available: null, special_tags: null,
    scraped_at: '2026-03-20T15:00:00Z', image_url: null,
    ...overrides,
  };
}

function makeRentedUnit(overrides: Partial<RentedUnit> = {}): RentedUnit {
  return {
    unit_id: '2308', floorplan_name: 'A1 Villas',
    floor: 2, bedrooms: 0, last_price: 1229,
    last_available_date: '2026-04-01', last_seen: '2026-03-19',
    ...overrides,
  };
}

function makeUnit(overrides: Partial<Unit> = {}): Unit {
  return {
    complex_id: 1, complex_name: 'Camden Greenville',
    floorplan_name: 'A1 Villas', floorplan_slug: 'a1-villas-floor-plan',
    unit_id: '2308', floor: 2, bedrooms: 0, bathrooms: 1, sqft: 550,
    price: 1229, available_date: '2026-04-15', avail_note: null,
    special_tags: null, scraped_at: '2026-03-20T15:00:00Z',
    ...overrides,
  };
}

const mockApi = {
  complexes:         () => of([]),
  floorPlans:        () => of([]),
  leaseTerms:        () => of([14, 6, 5, 4]),
  rented:            () => of([]),
  unitsForFloorPlan: () => of([]),
  floorPlanHistory:  () => of([]),
};

function setup() {
  TestBed.configureTestingModule({
    providers: [
      DashboardStateService,
      { provide: ApiService, useValue: mockApi },
      provideHttpClient(),
      provideHttpClientTesting(),
    ],
  });
  return TestBed.inject(DashboardStateService);
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('DashboardStateService', () => {

  // ── bedroomLabel ──────────────────────────────────────────────────────────

  describe('bedroomLabel()', () => {
    it('returns Studio for 0', () => {
      expect(setup().bedroomLabel(0)).toBe('Studio');
    });

    it('returns 1 Bedroom for 1', () => {
      expect(setup().bedroomLabel(1)).toBe('1 Bedroom');
    });

    it('returns N Bedrooms for N > 1', () => {
      const s = setup();
      expect(s.bedroomLabel(2)).toBe('2 Bedrooms');
      expect(s.bedroomLabel(3)).toBe('3 Bedrooms');
    });
  });

  // ── formatDate ────────────────────────────────────────────────────────────

  describe('formatDate()', () => {
    it('returns — for null', () => {
      expect(setup().formatDate(null)).toBe('—');
    });

    it('returns Available Now for past dates', () => {
      expect(setup().formatDate('2020-01-01')).toBe('Available Now');
    });

    it('returns formatted date for future dates', () => {
      const result = setup().formatDate('2099-06-15');
      expect(result).toContain('Jun');
      expect(result).toContain('15');
    });
  });

  // ── planKey ───────────────────────────────────────────────────────────────

  describe('planKey()', () => {
    it('returns complexId:floorplanName', () => {
      const fp = makeFloorPlan({ complex_id: 2, floorplan_name: 'TH2 Flats' });
      expect(setup().planKey(fp)).toBe('2:TH2 Flats');
    });
  });

  // ── rentedByFloorPlan ─────────────────────────────────────────────────────

  describe('rentedByFloorPlan()', () => {
    it('returns empty map when no rented units', () => {
      const s = setup();
      s.rentedUnits.set([]);
      expect(s.rentedByFloorPlan().size).toBe(0);
    });

    it('groups units by floorplan_name', () => {
      const s = setup();
      s.rentedUnits.set([
        makeRentedUnit({ unit_id: '2308', floorplan_name: 'A1 Villas' }),
        makeRentedUnit({ unit_id: '3309', floorplan_name: 'A1 Villas' }),
        makeRentedUnit({ unit_id: '122',  floorplan_name: 'TH1 Flats' }),
      ]);
      const map = s.rentedByFloorPlan();
      expect(map.get('A1 Villas')?.length).toBe(2);
      expect(map.get('TH1 Flats')?.length).toBe(1);
    });
  });

  // ── displayFiltered ───────────────────────────────────────────────────────

  describe('displayFiltered()', () => {
    it('uses available unit counts when status is available', () => {
      const s = setup();
      s.floorPlans.set([makeFloorPlan({ available_units: 3, min_price: 1229, max_price: 1289 })]);
      s.selectedStatus.set('available');
      const result = s.displayFiltered();
      expect(result[0].display_units).toBe(3);
      expect(result[0].display_min).toBe(1229);
      expect(result[0].display_max).toBe(1289);
    });

    it('uses rented counts and prices when status is rented', () => {
      const s = setup();
      s.floorPlans.set([makeFloorPlan({ available_units: 3, min_price: 1229, max_price: 1289 })]);
      s.rentedUnits.set([
        makeRentedUnit({ floorplan_name: 'A1 Villas', last_price: 1200 }),
        makeRentedUnit({ floorplan_name: 'A1 Villas', last_price: 1250, unit_id: '9999' }),
      ]);
      s.selectedStatus.set('rented');
      const result = s.displayFiltered();
      expect(result[0].display_units).toBe(2);
      expect(result[0].display_min).toBe(1200);
      expect(result[0].display_max).toBe(1250);
    });

    it('combines counts and full price range when status is all', () => {
      const s = setup();
      s.floorPlans.set([makeFloorPlan({ available_units: 3, min_price: 1249, max_price: 1289 })]);
      s.rentedUnits.set([makeRentedUnit({ floorplan_name: 'A1 Villas', last_price: 1229 })]);
      s.selectedStatus.set('all');
      const result = s.displayFiltered();
      expect(result[0].display_units).toBe(4);
      expect(result[0].display_min).toBe(1229);
      expect(result[0].display_max).toBe(1289);
    });

    it('filters out floor plans with 0 display_units', () => {
      const s = setup();
      s.floorPlans.set([
        makeFloorPlan({ floorplan_name: 'A1 Villas', available_units: 2 }),
        makeFloorPlan({ floorplan_name: 'TH1 Flats', available_units: 1 }),
      ]);
      s.rentedUnits.set([makeRentedUnit({ floorplan_name: 'A1 Villas' })]);
      s.selectedStatus.set('rented');
      const result = s.displayFiltered();
      expect(result.length).toBe(1);
      expect(result[0].floorplan_name).toBe('A1 Villas');
    });

    it('applies bedroom filter before status logic', () => {
      const s = setup();
      s.floorPlans.set([
        makeFloorPlan({ floorplan_name: 'A1 Villas', bedrooms: 0, available_units: 2 }),
        makeFloorPlan({ floorplan_name: 'TH2 Flats', bedrooms: 2, available_units: 4 }),
      ]);
      s.selectedBedrooms.set(2);
      s.selectedStatus.set('available');
      const result = s.displayFiltered();
      expect(result.length).toBe(1);
      expect(result[0].floorplan_name).toBe('TH2 Flats');
    });
  });

  // ── totalUnits ────────────────────────────────────────────────────────────

  describe('totalUnits()', () => {
    it('sums display_units across displayed floor plans', () => {
      const s = setup();
      s.floorPlans.set([
        makeFloorPlan({ floorplan_name: 'A1 Villas', available_units: 3 }),
        makeFloorPlan({ floorplan_name: 'A3 Villas', available_units: 5 }),
      ]);
      s.selectedStatus.set('available');
      expect(s.totalUnits()).toBe(8);
    });

    it('reflects rented counts when status is rented', () => {
      const s = setup();
      s.floorPlans.set([makeFloorPlan({ floorplan_name: 'A1 Villas', available_units: 3 })]);
      s.rentedUnits.set([
        makeRentedUnit({ floorplan_name: 'A1 Villas', unit_id: 'u1' }),
        makeRentedUnit({ floorplan_name: 'A1 Villas', unit_id: 'u2' }),
      ]);
      s.selectedStatus.set('rented');
      expect(s.totalUnits()).toBe(2);
    });
  });

  // ── cheapestUnit ──────────────────────────────────────────────────────────

  describe('cheapestUnit()', () => {
    it('returns null when no floor plans', () => {
      const s = setup();
      s.floorPlans.set([]);
      expect(s.cheapestUnit()).toBeNull();
    });

    it('returns the floor plan with the lowest display_min', () => {
      const s = setup();
      s.floorPlans.set([
        makeFloorPlan({ floorplan_name: 'TH2 Flats', min_price: 2659, max_price: 2839, available_units: 4 }),
        makeFloorPlan({ floorplan_name: 'A1 Villas', min_price: 1229, max_price: 1289, available_units: 3 }),
      ]);
      s.selectedStatus.set('available');
      expect(s.cheapestUnit()?.floorplan_name).toBe('A1 Villas');
    });
  });

  // ── expandedDisplayUnits ──────────────────────────────────────────────────

  describe('expandedDisplayUnits()', () => {
    it('returns only available units when status is available', () => {
      const s = setup();
      s.expandedFloorPlanName.set('A1 Villas');
      s.expandedUnits.set([makeUnit({ unit_id: '2308' })]);
      s.rentedUnits.set([makeRentedUnit({ floorplan_name: 'A1 Villas', unit_id: '9999' })]);
      s.selectedStatus.set('available');
      const result = s.expandedDisplayUnits();
      expect(result.length).toBe(1);
      expect(result[0].unit_id).toBe('2308');
      expect(result[0].status).toBe('available');
    });

    it('returns only rented units for this floor plan when status is rented', () => {
      const s = setup();
      s.expandedFloorPlanName.set('A1 Villas');
      s.expandedUnits.set([makeUnit({ unit_id: '2308' })]);
      s.rentedUnits.set([
        makeRentedUnit({ floorplan_name: 'A1 Villas', unit_id: '9999' }),
        makeRentedUnit({ floorplan_name: 'TH1 Flats', unit_id: '122' }),
      ]);
      s.selectedStatus.set('rented');
      const result = s.expandedDisplayUnits();
      expect(result.length).toBe(1);
      expect(result[0].unit_id).toBe('9999');
      expect(result[0].status).toBe('rented');
      expect(result[0].last_seen).toBe('2026-03-19');
    });

    it('returns all units combined when status is all', () => {
      const s = setup();
      s.expandedFloorPlanName.set('A1 Villas');
      s.expandedUnits.set([makeUnit({ unit_id: '2308' })]);
      s.rentedUnits.set([makeRentedUnit({ floorplan_name: 'A1 Villas', unit_id: '9999' })]);
      s.selectedStatus.set('all');
      const result = s.expandedDisplayUnits();
      expect(result.length).toBe(2);
      expect(result.map(u => u.status)).toEqual(['available', 'rented']);
    });

    it('maps rented unit fields correctly', () => {
      const s = setup();
      s.expandedFloorPlanName.set('A1 Villas');
      s.expandedUnits.set([]);
      s.rentedUnits.set([
        makeRentedUnit({ floorplan_name: 'A1 Villas', unit_id: '2308', last_price: 1299, floor: 3, last_seen: '2026-03-19' }),
      ]);
      s.selectedStatus.set('rented');
      const unit = s.expandedDisplayUnits()[0];
      expect(unit.unit_id).toBe('2308');
      expect(unit.price).toBe(1299);
      expect(unit.floor).toBe(3);
      expect(unit.last_seen).toBe('2026-03-19');
    });
  });

  // ── togglePlan ────────────────────────────────────────────────────────────

  describe('togglePlan()', () => {
    it('sets expandedPlan and expandedFloorPlanName when opening', () => {
      const s = setup();
      const fp = makeFloorPlan({ complex_id: 1, floorplan_name: 'A1 Villas' });
      s.togglePlan(fp);
      expect(s.expandedPlan()).toBe('1:A1 Villas');
      expect(s.expandedFloorPlanName()).toBe('A1 Villas');
    });

    it('collapses when toggling the same plan again', () => {
      const s = setup();
      const fp = makeFloorPlan({ complex_id: 1, floorplan_name: 'A1 Villas' });
      s.togglePlan(fp);
      s.togglePlan(fp);
      expect(s.expandedPlan()).toBeNull();
      expect(s.expandedFloorPlanName()).toBeNull();
    });
  });

  // ── headerSubtitle ────────────────────────────────────────────────────────

  describe('headerSubtitle()', () => {
    it('returns Dallas, TX when no complex selected', () => {
      const s = setup();
      s.selectedComplexId.set(null);
      expect(s.headerSubtitle()).toBe('Dallas, TX');
    });

    it('returns complex display_name when a complex is selected', () => {
      const s = setup();
      s.complexes.set([{ id: 1, name: 'camden', display_name: 'Camden Greenville', city: 'Dallas', state: 'TX', url: null }]);
      s.selectedComplexId.set(1);
      expect(s.headerSubtitle()).toBe('Camden Greenville');
    });
  });
});

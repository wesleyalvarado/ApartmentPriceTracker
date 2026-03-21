import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { ApiService } from './api.service';

const BASE = 'http://localhost:8000/api';

describe('ApiService', () => {
  let service: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ApiService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  // ── latest ─────────────────────────────────────────────────────────────────

  it('latest() — no params when no args', () => {
    service.latest().subscribe();
    const req = http.expectOne(`${BASE}/latest`);
    expect(req.request.params.keys().length).toBe(0);
    req.flush([]);
  });

  it('latest(1) — includes bedrooms param', () => {
    service.latest(1).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/latest`);
    expect(req.request.params.get('bedrooms')).toBe('1');
    req.flush([]);
  });

  it('latest(0) — includes bedrooms=0 (Studio)', () => {
    service.latest(0).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/latest`);
    expect(req.request.params.get('bedrooms')).toBe('0');
    req.flush([]);
  });

  it('latest(undefined, 1500) — includes max_price param', () => {
    service.latest(undefined, 1500).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/latest`);
    expect(req.request.params.get('max_price')).toBe('1500');
    req.flush([]);
  });

  it('latest(2, 2000, 1) — includes all three params', () => {
    service.latest(2, 2000, 1).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/latest`);
    expect(req.request.params.get('bedrooms')).toBe('2');
    expect(req.request.params.get('max_price')).toBe('2000');
    expect(req.request.params.get('complex_id')).toBe('1');
    req.flush([]);
  });

  // ── complexes ──────────────────────────────────────────────────────────────

  it('complexes() — GET /api/complexes', () => {
    service.complexes().subscribe();
    const req = http.expectOne(`${BASE}/complexes`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  // ── floorPlans ─────────────────────────────────────────────────────────────

  it('floorPlans() — no params when leaseTerm is 15 and no complexId', () => {
    service.floorPlans(15).subscribe();
    const req = http.expectOne(`${BASE}/floorplans`);
    expect(req.request.params.keys().length).toBe(0);
    req.flush([]);
  });

  it('floorPlans(4) — includes lease_term param', () => {
    service.floorPlans(4).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/floorplans`);
    expect(req.request.params.get('lease_term')).toBe('4');
    req.flush([]);
  });

  it('floorPlans(15, 1) — includes complex_id but not lease_term', () => {
    service.floorPlans(15, 1).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/floorplans`);
    expect(req.request.params.get('complex_id')).toBe('1');
    expect(req.request.params.has('lease_term')).toBeFalse();
    req.flush([]);
  });

  it('floorPlans(6, 2) — includes both lease_term and complex_id', () => {
    service.floorPlans(6, 2).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/floorplans`);
    expect(req.request.params.get('lease_term')).toBe('6');
    expect(req.request.params.get('complex_id')).toBe('2');
    req.flush([]);
  });

  // ── leaseTerms ─────────────────────────────────────────────────────────────

  it('leaseTerms() — no params when no complexId', () => {
    service.leaseTerms().subscribe();
    const req = http.expectOne(`${BASE}/lease_terms`);
    expect(req.request.params.keys().length).toBe(0);
    req.flush([]);
  });

  it('leaseTerms(1) — includes complex_id', () => {
    service.leaseTerms(1).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/lease_terms`);
    expect(req.request.params.get('complex_id')).toBe('1');
    req.flush([]);
  });

  // ── unitsForFloorPlan ──────────────────────────────────────────────────────

  it('unitsForFloorPlan() — encodes floor plan name in URL', () => {
    service.unitsForFloorPlan('A1 Villas').subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/units/A1%20Villas`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('unitsForFloorPlan() — includes lease_term when not 15', () => {
    service.unitsForFloorPlan('A1 Villas', 4).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/units/A1%20Villas`);
    expect(req.request.params.get('lease_term')).toBe('4');
    req.flush([]);
  });

  it('unitsForFloorPlan() — omits lease_term when 15', () => {
    service.unitsForFloorPlan('A1 Villas', 15).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/units/A1%20Villas`);
    expect(req.request.params.has('lease_term')).toBeFalse();
    req.flush([]);
  });

  it('unitsForFloorPlan() — includes complex_id when provided', () => {
    service.unitsForFloorPlan('A1 Villas', 15, 1).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/units/A1%20Villas`);
    expect(req.request.params.get('complex_id')).toBe('1');
    req.flush([]);
  });

  // ── floorPlanHistory ───────────────────────────────────────────────────────

  it('floorPlanHistory() — encodes name and includes days', () => {
    service.floorPlanHistory('TH2 Flats', 60).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/history/floorplan/TH2%20Flats`);
    expect(req.request.params.get('days')).toBe('60');
    req.flush([]);
  });

  it('floorPlanHistory() — includes complex_id when provided', () => {
    service.floorPlanHistory('TH2 Flats', 30, 1).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/history/floorplan/TH2%20Flats`);
    expect(req.request.params.get('complex_id')).toBe('1');
    req.flush([]);
  });

  // ── unitHistory ────────────────────────────────────────────────────────────

  it('unitHistory() — GET /api/history/{id} with days in URL', () => {
    service.unitHistory('122', 30).subscribe();
    // days is appended inline so it appears in the full URL
    const req = http.expectOne(`${BASE}/history/122?days=30`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  // ── rented ─────────────────────────────────────────────────────────────────

  it('rented() — GET /api/rented with default days=14', () => {
    service.rented().subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/rented`);
    expect(req.request.params.get('days')).toBe('14');
    req.flush([]);
  });

  it('rented(null, 7) — uses provided days and omits complex_id', () => {
    service.rented(null, 7).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/rented`);
    expect(req.request.params.get('days')).toBe('7');
    expect(req.request.params.has('complex_id')).toBeFalse();
    req.flush([]);
  });

  it('rented(1) — includes complex_id', () => {
    service.rented(1).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/rented`);
    expect(req.request.params.get('complex_id')).toBe('1');
    req.flush([]);
  });

  // ── stats ──────────────────────────────────────────────────────────────────

  it('stats() — GET /api/stats', () => {
    service.stats().subscribe();
    const req = http.expectOne(`${BASE}/stats`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  // ── priceDrops ─────────────────────────────────────────────────────────────

  it('priceDrops() — no params when no args', () => {
    service.priceDrops().subscribe();
    const req = http.expectOne(`${BASE}/price-drops`);
    expect(req.request.params.keys().length).toBe(0);
    req.flush([]);
  });

  it('priceDrops(4) — includes lease_term param', () => {
    service.priceDrops(4).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/price-drops`);
    expect(req.request.params.get('lease_term')).toBe('4');
    req.flush([]);
  });

  it('priceDrops(15) — omits lease_term when 15', () => {
    service.priceDrops(15).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/price-drops`);
    expect(req.request.params.has('lease_term')).toBeFalse();
    req.flush([]);
  });

  it('priceDrops(null, 1) — includes complex_id', () => {
    service.priceDrops(null, 1).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/price-drops`);
    expect(req.request.params.get('complex_id')).toBe('1');
    req.flush([]);
  });

  // ── housePriceSummary ──────────────────────────────────────────────────────

  it('housePriceSummary() — GET /api/house-prices/summary', () => {
    service.housePriceSummary().subscribe();
    const req = http.expectOne(`${BASE}/house-prices/summary`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  // ── zhviTrend ──────────────────────────────────────────────────────────────

  it('zhviTrend() — includes default home_type and months', () => {
    service.zhviTrend().subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/house-prices/zhvi`);
    expect(req.request.params.get('home_type')).toBe('all_middle_tier');
    expect(req.request.params.get('months')).toBe('24');
    req.flush([]);
  });

  it('zhviTrend("3bed", 12) — uses provided params', () => {
    service.zhviTrend('3bed', 12).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/house-prices/zhvi`);
    expect(req.request.params.get('home_type')).toBe('3bed');
    expect(req.request.params.get('months')).toBe('12');
    req.flush([]);
  });

  // ── redfinMetrics ──────────────────────────────────────────────────────────

  it('redfinMetrics() — includes default months=12', () => {
    service.redfinMetrics().subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/house-prices/redfin`);
    expect(req.request.params.get('months')).toBe('12');
    req.flush([]);
  });

  it('redfinMetrics(24) — uses provided months', () => {
    service.redfinMetrics(24).subscribe();
    const req = http.expectOne(r => r.url === `${BASE}/house-prices/redfin`);
    expect(req.request.params.get('months')).toBe('24');
    req.flush([]);
  });
});

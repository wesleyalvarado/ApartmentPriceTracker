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
});

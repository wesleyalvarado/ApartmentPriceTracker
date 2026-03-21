import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Complex, FloorPlan, Unit, PricePoint, Stats, RentedUnit, PriceDrop, HousePriceSummary, ZhviPoint, RedfinPoint } from '../models/apartment.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = 'http://localhost:8000/api';

  complexes(): Observable<Complex[]> {
    return this.http.get<Complex[]>(`${this.base}/complexes`);
  }

  floorPlans(leaseTerm?: number, complexId?: number | null): Observable<FloorPlan[]> {
    let params = new HttpParams();
    if (leaseTerm && leaseTerm !== 15) params = params.set('lease_term', leaseTerm);
    if (complexId) params = params.set('complex_id', complexId);
    return this.http.get<FloorPlan[]>(`${this.base}/floorplans`, { params });
  }

  latest(bedrooms?: number, maxPrice?: number, complexId?: number | null): Observable<Unit[]> {
    let params = new HttpParams();
    if (bedrooms !== undefined) params = params.set('bedrooms', bedrooms);
    if (maxPrice !== undefined) params = params.set('max_price', maxPrice);
    if (complexId) params = params.set('complex_id', complexId);
    return this.http.get<Unit[]>(`${this.base}/latest`, { params });
  }

  unitsForFloorPlan(name: string, leaseTerm?: number, complexId?: number | null): Observable<Unit[]> {
    let params = new HttpParams();
    if (leaseTerm && leaseTerm !== 15) params = params.set('lease_term', leaseTerm);
    if (complexId) params = params.set('complex_id', complexId);
    return this.http.get<Unit[]>(`${this.base}/units/${encodeURIComponent(name)}`, { params });
  }

  unitHistory(unitId: string, days = 30): Observable<PricePoint[]> {
    return this.http.get<PricePoint[]>(`${this.base}/history/${unitId}?days=${days}`);
  }

  floorPlanHistory(name: string, days = 30, complexId?: number | null): Observable<PricePoint[]> {
    let params = new HttpParams().set('days', days);
    if (complexId) params = params.set('complex_id', complexId);
    return this.http.get<PricePoint[]>(
      `${this.base}/history/floorplan/${encodeURIComponent(name)}`, { params }
    );
  }

  leaseTerms(complexId?: number | null): Observable<number[]> {
    let params = new HttpParams();
    if (complexId) params = params.set('complex_id', complexId);
    return this.http.get<number[]>(`${this.base}/lease_terms`, { params });
  }

  rented(complexId?: number | null, days = 14): Observable<RentedUnit[]> {
    let params = new HttpParams().set('days', days);
    if (complexId) params = params.set('complex_id', complexId);
    return this.http.get<RentedUnit[]>(`${this.base}/rented`, { params });
  }

  priceDrops(leaseTerm?: number | null, complexId?: number | null): Observable<PriceDrop[]> {
    let params = new HttpParams();
    if (leaseTerm && leaseTerm !== 15) params = params.set('lease_term', leaseTerm);
    if (complexId) params = params.set('complex_id', complexId);
    return this.http.get<PriceDrop[]>(`${this.base}/price-drops`, { params });
  }

  stats(): Observable<Stats[]> {
    return this.http.get<Stats[]>(`${this.base}/stats`);
  }

  housePriceSummary(): Observable<HousePriceSummary[]> {
    return this.http.get<HousePriceSummary[]>(`${this.base}/house-prices/summary`);
  }

  zhviTrend(homeType = 'all_middle_tier', months = 24): Observable<ZhviPoint[]> {
    const params = new HttpParams().set('home_type', homeType).set('months', months);
    return this.http.get<ZhviPoint[]>(`${this.base}/house-prices/zhvi`, { params });
  }

  redfinMetrics(months = 12): Observable<RedfinPoint[]> {
    const params = new HttpParams().set('months', months);
    return this.http.get<RedfinPoint[]>(`${this.base}/house-prices/redfin`, { params });
  }
}

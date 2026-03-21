import { Injectable, inject, signal, computed } from '@angular/core';
import { ApiService } from './api.service';
import {
  Complex, FloorPlan, Unit, PricePoint, RentedUnit,
  DisplayUnit, DisplayFloorPlan, StatusValue,
} from '../models/apartment.model';

// Option interfaces exported so FilterBarComponent can type its @Inputs
export interface BedroomOption      { label: string; value: number | null; }
export interface LeaseTermOption    { label: string; value: number; }
export interface ComplexOption      { label: string; value: number | null; }
export interface AvailabilityOption { label: string; value: number | null; }
export interface StatusOption       { label: string; value: StatusValue; }

@Injectable({ providedIn: 'root' })
export class DashboardStateService {
  private api = inject(ApiService);

  // ── Signals ────────────────────────────────────────────────────────────────
  complexes             = signal<Complex[]>([]);
  floorPlans            = signal<FloorPlan[]>([]);
  loading               = signal(true);
  selectedBedrooms      = signal<number | null>(null);
  selectedLeaseTerm     = signal<number>(15);
  selectedAvailability  = signal<number | null>(null);
  selectedComplexId     = signal<number | null>(null);
  expandedPlan          = signal<string | null>(null);
  expandedFloorPlanName = signal<string | null>(null);
  expandedUnits         = signal<Unit[]>([]);
  expandedHistory       = signal<PricePoint[]>([]);
  loadingUnits          = signal(false);
  rentedUnits           = signal<RentedUnit[]>([]);
  selectedStatus        = signal<StatusValue>('available');
  availableLeaseTerms   = signal<number[]>([15, 14, 6, 5, 4]);
  chartData             = signal<any>(null);

  // ── Static options ─────────────────────────────────────────────────────────
  readonly bedroomOptions: BedroomOption[] = [
    { label: 'All',    value: null },
    { label: 'Studio', value: 0 },
    { label: '1 BR',   value: 1 },
    { label: '2 BR',   value: 2 },
  ];

  readonly availabilityOptions: AvailabilityOption[] = [
    { label: 'Any',     value: null },
    { label: 'Now',     value: 0 },
    { label: '30 days', value: 30 },
    { label: '60 days', value: 60 },
    { label: '90 days', value: 90 },
  ];

  readonly allLeaseTermOptions: LeaseTermOption[] = [
    { label: '15 mo', value: 15 },
    { label: '14 mo', value: 14 },
    { label: '6 mo',  value: 6 },
    { label: '5 mo',  value: 5 },
    { label: '4 mo',  value: 4 },
  ];

  readonly statusOptions: StatusOption[] = [
    { label: 'Available', value: 'available' },
    { label: 'Rented',    value: 'rented' },
    { label: 'All',       value: 'all' },
  ];

  readonly chartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx: any) => `$${ctx.raw.toLocaleString()}` } },
    },
    scales: {
      x: { ticks: { font: { size: 11 } } },
      y: { ticks: { callback: (v: number) => `$${v.toLocaleString()}`, font: { size: 11 } } },
    },
  };

  // ── Computed ───────────────────────────────────────────────────────────────
  complexOptions = computed<ComplexOption[]>(() => [
    { label: 'All', value: null },
    ...this.complexes().map(c => ({ label: c.display_name, value: c.id })),
  ]);

  leaseTermOptions = computed<LeaseTermOption[]>(() =>
    this.allLeaseTermOptions.filter(o => this.availableLeaseTerms().includes(o.value))
  );

  showComplexBadge = computed(() =>
    this.selectedComplexId() === null && this.complexes().length > 1
  );

  headerSubtitle = computed(() => {
    const id = this.selectedComplexId();
    if (id === null) return 'Dallas, TX';
    const cx = this.complexes().find(c => c.id === id);
    return cx ? cx.display_name : 'Dallas, TX';
  });

  lastScraped = computed(() => {
    const plans = this.floorPlans();
    if (!plans.length) return null;
    return new Date(plans[0].scraped_at);
  });

  rentedByFloorPlan = computed(() => {
    const map = new Map<string, RentedUnit[]>();
    for (const u of this.rentedUnits()) {
      if (!map.has(u.floorplan_name)) map.set(u.floorplan_name, []);
      map.get(u.floorplan_name)!.push(u);
    }
    return map;
  });

  filtered = computed(() => {
    const br    = this.selectedBedrooms();
    const days  = this.selectedAvailability();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return this.floorPlans().filter(fp => {
      if (br !== null && fp.bedrooms !== br) return false;
      if (days !== null) {
        if (!fp.earliest_available) return true;
        const avail  = new Date(fp.earliest_available + 'T00:00:00');
        const cutoff = new Date(today);
        cutoff.setDate(cutoff.getDate() + days);
        if (avail > cutoff) return false;
      }
      return true;
    });
  });

  displayFiltered = computed<DisplayFloorPlan[]>(() => {
    const status    = this.selectedStatus();
    const rentedMap = this.rentedByFloorPlan();

    return this.filtered().map(fp => {
      const rented       = rentedMap.get(fp.floorplan_name) ?? [];
      const rentedPrices = rented.map(r => r.last_price);
      const rentedMin    = rentedPrices.length ? Math.min(...rentedPrices) : null;
      const rentedMax    = rentedPrices.length ? Math.max(...rentedPrices) : null;

      if (status === 'rented') {
        return { ...fp, display_units: rented.length, display_min: rentedMin ?? fp.min_price, display_max: rentedMax ?? fp.max_price };
      } else if (status === 'all') {
        return {
          ...fp,
          display_units: fp.available_units + rented.length,
          display_min: Math.min(fp.min_price, rentedMin ?? fp.min_price),
          display_max: Math.max(fp.max_price, rentedMax ?? fp.max_price),
        };
      } else {
        return { ...fp, display_units: fp.available_units, display_min: fp.min_price, display_max: fp.max_price };
      }
    }).filter(fp => fp.display_units > 0);
  });

  totalUnits = computed(() =>
    this.displayFiltered().reduce((s, fp) => s + fp.display_units, 0)
  );

  cheapestUnit = computed(() => {
    const plans = this.displayFiltered();
    if (!plans.length) return null;
    return plans.reduce((min, fp) => fp.display_min < min.display_min ? fp : min);
  });

  // expandedDisplayUnits is scoped to whichever plan is currently open;
  // only the expanded card renders the panel so passing it to all cards is safe.
  expandedDisplayUnits = computed<DisplayUnit[]>(() => {
    const status = this.selectedStatus();
    const fpName = this.expandedFloorPlanName();

    const available: DisplayUnit[] = this.expandedUnits().map(u => ({
      unit_id: u.unit_id, floor: u.floor, price: u.price,
      available_date: u.available_date, status: 'available',
    }));

    const rented: DisplayUnit[] = this.rentedUnits()
      .filter(r => r.floorplan_name === fpName)
      .map(r => ({
        unit_id: r.unit_id, floor: r.floor, price: r.last_price,
        available_date: r.last_available_date, status: 'rented', last_seen: r.last_seen,
      }));

    if (status === 'available') return available;
    if (status === 'rented')    return rented;
    return [...available, ...rented];
  });

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  initialize() {
    this.api.complexes().subscribe(complexes => this.complexes.set(complexes));
    this._loadLeaseTerms();
    this._loadFloorPlans();
    this._loadRented();
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  onComplexChange(complexId: number | null) {
    this.selectedComplexId.set(complexId);
    this._collapseExpanded();
    this._loadLeaseTerms();
    this._loadFloorPlans();
  }

  onLeaseTermChange(term: number) {
    this.selectedLeaseTerm.set(term);
    this._collapseExpanded();
    this._loadFloorPlans();
  }

  planKey(fp: FloorPlan): string {
    return `${fp.complex_id}:${fp.floorplan_name}`;
  }

  togglePlan(fp: FloorPlan) {
    const key = this.planKey(fp);
    if (this.expandedPlan() === key) {
      this._collapseExpanded();
      return;
    }
    this.expandedPlan.set(key);
    this.expandedFloorPlanName.set(fp.floorplan_name);
    this.loadingUnits.set(true);
    this.expandedUnits.set([]);
    this.chartData.set(null);

    const term = this.selectedLeaseTerm();
    this.api.unitsForFloorPlan(fp.floorplan_name, term, fp.complex_id).subscribe(units => {
      this.expandedUnits.set(units);
      this.loadingUnits.set(false);
    });

    if (term === 15) {
      this.api.floorPlanHistory(fp.floorplan_name, 60, fp.complex_id).subscribe(history => {
        if (history.length >= 2) {
          this.chartData.set({
            labels: history.map(h => new Date(h.scraped_at).toLocaleDateString()),
            datasets: [{
              data: history.map(h => h.min_price),
              borderColor: '#2B5741',
              backgroundColor: 'rgba(43,87,65,.1)',
              borderWidth: 2, fill: true, tension: 0.4,
              pointBackgroundColor: '#2B5741', pointRadius: 4,
            }],
          });
        }
      });
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  bedroomLabel(n: number): string {
    if (n === 0) return 'Studio';
    if (n === 1) return '1 Bedroom';
    return `${n} Bedrooms`;
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso + 'T00:00:00');
    if (d <= new Date()) return 'Available Now';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  // ── Private ────────────────────────────────────────────────────────────────
  private _loadLeaseTerms() {
    this.api.leaseTerms(this.selectedComplexId()).subscribe(terms => {
      const show15   = this.selectedComplexId() === null || terms.includes(14);
      const allTerms = show15 ? [15, ...terms] : terms;
      this.availableLeaseTerms.set(allTerms);
      if (!allTerms.includes(this.selectedLeaseTerm())) {
        this.selectedLeaseTerm.set(allTerms[0]);
        this._loadFloorPlans();
      }
    });
  }

  private _loadFloorPlans() {
    this.loading.set(true);
    this.api.floorPlans(this.selectedLeaseTerm(), this.selectedComplexId()).subscribe({
      next:  fps => { this.floorPlans.set(fps); this.loading.set(false); },
      error: ()  => this.loading.set(false),
    });
  }

  private _loadRented() {
    this.api.rented(null, 14).subscribe({
      next:  units => this.rentedUnits.set(units),
      error: ()    => this.rentedUnits.set([]),
    });
  }

  private _collapseExpanded() {
    this.expandedPlan.set(null);
    this.expandedFloorPlanName.set(null);
    this.expandedUnits.set([]);
    this.chartData.set(null);
  }
}

import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { SelectButtonModule } from 'primeng/selectbutton';
import { TagModule } from 'primeng/tag';
import { SkeletonModule } from 'primeng/skeleton';
import { TooltipModule } from 'primeng/tooltip';
import { ChipModule } from 'primeng/chip';
import { DividerModule } from 'primeng/divider';
import { ChartModule } from 'primeng/chart';

import { ApiService } from '../../services/api.service';
import { Complex, FloorPlan, Unit, PricePoint, RentedUnit } from '../../models/apartment.model';

interface BedroomOption      { label: string; value: number | null; }
interface LeaseTermOption    { label: string; value: number; }
interface ComplexOption      { label: string; value: number | null; }
interface AvailabilityOption { label: string; value: number | null; }
interface StatusOption       { label: string; value: 'available' | 'rented' | 'all'; }

interface DisplayUnit {
  unit_id: string;
  floor: number | null;
  price: number;
  available_date: string | null;
  status: 'available' | 'rented';
  last_seen?: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    CardModule, TableModule, ButtonModule, SelectButtonModule,
    TagModule, SkeletonModule, TooltipModule, ChipModule,
    DividerModule, ChartModule,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  private api = inject(ApiService);

  // ── State ──────────────────────────────────────────────────────────────────
  complexes         = signal<Complex[]>([]);
  floorPlans        = signal<FloorPlan[]>([]);
  loading              = signal(true);
  selectedBedrooms     = signal<number | null>(null);
  selectedLeaseTerm    = signal<number>(15);
  selectedAvailability = signal<number | null>(null);
  selectedComplexId = signal<number | null>(null);
  expandedPlan          = signal<string | null>(null);  // key: "complexId:planName"
  expandedFloorPlanName = signal<string | null>(null);
  expandedUnits         = signal<Unit[]>([]);
  expandedHistory       = signal<PricePoint[]>([]);
  loadingUnits          = signal(false);
  rentedUnits           = signal<RentedUnit[]>([]);
  selectedStatus        = signal<'available' | 'rented' | 'all'>('available');

  bedroomOptions: BedroomOption[] = [
    { label: 'All',    value: null },
    { label: 'Studio', value: 0 },
    { label: '1 BR',   value: 1 },
    { label: '2 BR',   value: 2 },
  ];

  statusOptions: StatusOption[] = [
    { label: 'Available', value: 'available' },
    { label: 'Rented',    value: 'rented' },
    { label: 'All',       value: 'all' },
  ];

  availabilityOptions: AvailabilityOption[] = [
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

  availableLeaseTerms = signal<number[]>([15, 14, 6, 5, 4]);

  leaseTermOptions = computed<LeaseTermOption[]>(() =>
    this.allLeaseTermOptions.filter(o => this.availableLeaseTerms().includes(o.value))
  );

  // Built once complexes load
  complexOptions = computed<ComplexOption[]>(() => [
    { label: 'All', value: null },
    ...this.complexes().map(c => ({ label: c.display_name, value: c.id })),
  ]);

  // ngModel two-way binding shims (signals can't bind to ngModel directly)
  get selectedLeaseTermModel(): number { return this.selectedLeaseTerm(); }
  set selectedLeaseTermModel(v: number) { this.selectedLeaseTerm.set(v); }

  get selectedComplexIdModel(): number | null { return this.selectedComplexId(); }
  set selectedComplexIdModel(v: number | null) { this.selectedComplexId.set(v); }

  get selectedAvailabilityModel(): number | null { return this.selectedAvailability(); }
  set selectedAvailabilityModel(v: number | null) { this.selectedAvailability.set(v); }

  get selectedStatusModel(): 'available' | 'rented' | 'all' { return this.selectedStatus(); }
  set selectedStatusModel(v: 'available' | 'rented' | 'all') { this.selectedStatus.set(v); }

  // ── Derived ────────────────────────────────────────────────────────────────
  filtered = computed(() => {
    const br   = this.selectedBedrooms();
    const days = this.selectedAvailability();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return this.floorPlans().filter(fp => {
      if (br !== null && fp.bedrooms !== br) return false;
      if (days !== null) {
        if (!fp.earliest_available) return true; // no date = available now
        const avail = new Date(fp.earliest_available + 'T00:00:00');
        const cutoff = new Date(today);
        cutoff.setDate(cutoff.getDate() + days);
        if (avail > cutoff) return false;
      }
      return true;
    });
  });

  totalUnits = computed(() =>
    this.filtered().reduce((s, fp) => s + fp.available_units, 0)
  );

  cheapestUnit = computed(() => {
    const plans = this.filtered();
    if (!plans.length) return null;
    return plans.reduce((min, fp) => fp.min_price < min.min_price ? fp : min);
  });

  lastScraped = computed(() => {
    const plans = this.floorPlans();
    if (!plans.length) return null;
    return new Date(plans[0].scraped_at);
  });

  // Show complex badge on cards only when viewing "All" and >1 complex exists
  showComplexBadge = computed(() =>
    this.selectedComplexId() === null && this.complexes().length > 1
  );

  headerSubtitle = computed(() => {
    const id = this.selectedComplexId();
    if (id === null) return 'Dallas, TX';
    const cx = this.complexes().find(c => c.id === id);
    return cx ? cx.display_name : 'Dallas, TX';
  });

  expandedDisplayUnits = computed<DisplayUnit[]>(() => {
    const status  = this.selectedStatus();
    const fpName  = this.expandedFloorPlanName();

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

  // Chart data
  chartData = signal<any>(null);
  chartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: any) => `$${ctx.raw.toLocaleString()}`,
        },
      },
    },
    scales: {
      x: { ticks: { font: { size: 11 } } },
      y: {
        ticks: {
          callback: (v: number) => `$${v.toLocaleString()}`,
          font: { size: 11 },
        },
      },
    },
  };

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  ngOnInit() {
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

    // History chart only meaningful for 15-month default data
    if (term === 15) {
      this.api.floorPlanHistory(fp.floorplan_name, 60, fp.complex_id).subscribe(history => {
        if (history.length >= 2) {
          this.chartData.set({
            labels: history.map(h => new Date(h.scraped_at).toLocaleDateString()),
            datasets: [{
              data: history.map(h => h.min_price),
              borderColor: '#2B5741',
              backgroundColor: 'rgba(43,87,65,.1)',
              borderWidth: 2,
              fill: true,
              tension: 0.4,
              pointBackgroundColor: '#2B5741',
              pointRadius: 4,
            }],
          });
        }
      });
    }
  }

  private _loadLeaseTerms() {
    this.api.leaseTerms(this.selectedComplexId()).subscribe(terms => {
      // Show 15mo only when viewing all complexes or when 14mo exists (longer-term property)
      const show15 = this.selectedComplexId() === null || terms.includes(14);
      const allTerms = show15 ? [15, ...terms] : terms;
      this.availableLeaseTerms.set(allTerms);
      if (!allTerms.includes(this.selectedLeaseTerm())) {
        this.selectedLeaseTerm.set(allTerms[0]);
        this._loadFloorPlans();
      }
    });
  }

  private _collapseExpanded() {
    this.expandedPlan.set(null);
    this.expandedFloorPlanName.set(null);
    this.expandedUnits.set([]);
    this.chartData.set(null);
  }

  private _loadFloorPlans() {
    this.loading.set(true);
    this.api.floorPlans(this.selectedLeaseTerm(), this.selectedComplexId()).subscribe({
      next: fps => { this.floorPlans.set(fps); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  private _loadRented() {
    this.api.rented(null, 14).subscribe({
      next: units => this.rentedUnits.set(units),
      error: () => this.rentedUnits.set([]),
    });
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
}

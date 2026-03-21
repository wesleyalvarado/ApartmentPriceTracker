import { Component, OnInit, inject, signal, computed } from '@angular/core'; // computed used by zhviChartData, latestRedfin, redfinTableRows
import { CommonModule } from '@angular/common';
import { ChartModule } from 'primeng/chart';
import { SkeletonModule } from 'primeng/skeleton';
import { CardModule } from 'primeng/card';
import { TooltipModule } from 'primeng/tooltip';

import { ApiService } from '../../services/api.service';
import { HousePriceSummary, ZhviPoint, RedfinPoint } from '../../models/apartment.model';
import { AffordabilityCalculatorComponent } from '../affordability-calculator/affordability-calculator.component';

@Component({
  selector: 'app-house-prices',
  standalone: true,
  imports: [CommonModule, ChartModule, SkeletonModule, CardModule, TooltipModule, AffordabilityCalculatorComponent],
  styleUrl: './house-prices.component.scss',
  template: `
    <!-- Header -->
    <header class="hp-header">
      <div class="hp-header-inner">
        <div class="header-brand">
          <div class="header-logo"><i class="pi pi-home"></i></div>
          <div>
            <div class="header-title">House Price Tracker</div>
            <div class="header-sub">M Streets · Lakewood · Lake Highlands — Dallas, TX</div>
          </div>
        </div>
        <div class="header-meta"><i class="pi pi-database"></i> Zillow ZHVI + Redfin</div>
      </div>
    </header>

    <!-- Filters -->
    <div class="hp-filters">
      <div class="hp-filters-inner">
        <div class="filter-group">
          <span class="filter-label">Home Type</span>
          <div class="btn-group">
            @for (opt of homeTypeOptions; track opt.value) {
              <button [class.active]="selectedHomeType() === opt.value"
                      (click)="onHomeTypeChange(opt.value)">{{ opt.label }}</button>
            }
          </div>
        </div>
        <div class="filter-group">
          <span class="filter-label">History</span>
          <div class="btn-group">
            @for (opt of monthOptions; track opt.value) {
              <button [class.active]="selectedMonths() === opt.value"
                      (click)="onMonthsChange(opt.value)">{{ opt.label }}</button>
            }
          </div>
        </div>
      </div>
    </div>

    <!-- Stats bar -->
    @if (loading()) {
      <div class="hp-stats">
        @for (i of [1, 2, 3]; track i) {
          <p-skeleton height="80px" />
        }
      </div>
    } @else if (summary().length) {
      <div class="hp-stats">
        @for (s of summary(); track s.zip_code; let last = $last) {
          <div class="zip-stat">
            <div class="zip-stat-name">{{ s.display_name ?? s.zip_code }}</div>
            <div class="zip-stat-value">
              {{ s.zhvi_current ? ('$' + formatK(s.zhvi_current)) : '—' }}
            </div>
            <div class="zip-stat-label">Median Home Value (ZHVI)</div>
            <div class="zip-stat-meta">
              @if (s.days_on_market) {
                <span>{{ s.days_on_market | number:'1.0-1' }} days on market</span>
              }
              @if (s.inventory) {
                <span>{{ s.inventory }} active</span>
              }
            </div>
          </div>
          @if (!last) { <div class="stat-divider"></div> }
        }
      </div>
    } @else {
      <div class="no-data-banner">
        <i class="pi pi-info-circle"></i>
        No data yet — run <code>python scraper/house_prices/ingest_zhvi.py</code> to load Zillow data
      </div>
    }

    <!-- Main content -->
    <main class="hp-main">
      <div class="hp-grid">

        <!-- ZHVI Chart -->
        <div class="hp-card">
          <div class="section-label"><i class="pi pi-chart-line"></i> Median Home Value Trend</div>
          @if (zhviChartData()) {
            <div class="chart-container">
              <p-chart type="line"
                       [data]="zhviChartData()"
                       [options]="zhviChartOptions"
                       height="280px" />
            </div>
          } @else {
            <div class="chart-placeholder">
              <i class="pi pi-chart-line"></i>
              Run ingest_zhvi.py to populate trend data
            </div>
          }
        </div>

        <!-- Affordability Calculator -->
        <app-affordability-calculator />
      </div>

      <!-- Redfin latest metrics -->
      @if (redfinTableRows().length) {
        <div class="hp-card redfin-card">
          <div class="section-label"><i class="pi pi-table"></i> Latest Market Metrics (Redfin)</div>
          <div class="redfin-table">
            <div class="redfin-header-row">
              <div></div>
              @for (h of redfinHeaders; track h.zip) {
                <div class="redfin-header">{{ h.label }}<br><small>{{ h.zip }}</small></div>
              }
            </div>
            @for (row of redfinTableRows(); track row.label) {
              <div class="redfin-row">
                <div class="redfin-row-label">{{ row.label }}</div>
                @for (val of row.values; track $index) {
                  <div class="redfin-cell">{{ val }}</div>
                }
              </div>
            }
          </div>
        </div>
      }
    </main>
  `,
})
export class HousePricesComponent implements OnInit {
  private api = inject(ApiService);

  summary  = signal<HousePriceSummary[]>([]);
  zhvi     = signal<ZhviPoint[]>([]);
  redfin   = signal<RedfinPoint[]>([]);
  loading  = signal(true);

  selectedHomeType = signal('all_middle_tier');
  selectedMonths   = signal(24);

  readonly homeTypeOptions = [
    { label: 'All Homes',  value: 'all_middle_tier' },
    { label: '3-Bedroom',  value: '3bed' },
    { label: 'SFR Only',   value: 'sfr_only' },
  ];

  readonly monthOptions = [
    { label: '12 mo', value: 12 },
    { label: '24 mo', value: 24 },
    { label: '36 mo', value: 36 },
    { label: '60 mo', value: 60 },
  ];

  readonly redfinHeaders = [
    { zip: '75206', label: 'M Streets' },
    { zip: '75214', label: 'Lakewood' },
    { zip: '75238', label: 'Lake Highlands' },
  ];

  readonly zhviChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
      tooltip: {
        callbacks: {
          label: (ctx: any) => ` ${ctx.dataset.label}: $${Math.round(ctx.raw).toLocaleString()}`,
        },
      },
    },
    scales: {
      x: { ticks: { maxTicksLimit: 12, font: { size: 10 } } },
      y: {
        ticks: {
          callback: (v: number) => `$${(v / 1000).toFixed(0)}K`,
          font: { size: 11 },
        },
      },
    },
  };

  zhviChartData = computed(() => {
    const data = this.zhvi();
    if (!data.length) return null;
    const grouped = new Map<string, ZhviPoint[]>();
    for (const d of data) {
      if (!grouped.has(d.zip_code)) grouped.set(d.zip_code, []);
      grouped.get(d.zip_code)!.push(d);
    }
    const ZIP_META = [
      { zip: '75206', label: 'M Streets (75206)',      color: '#3B82F6' },
      { zip: '75214', label: 'Lakewood (75214)',        color: '#10B981' },
      { zip: '75238', label: 'Lake Highlands (75238)', color: '#F59E0B' },
    ];
    const labelsZip = ZIP_META.find(z => grouped.has(z.zip))?.zip ?? '';
    const labels = grouped.get(labelsZip)?.map(d => {
      const [y, m] = d.month.split('-');
      return `${m}/${y.slice(2)}`;
    }) ?? [];
    return {
      labels,
      datasets: ZIP_META.filter(z => grouped.has(z.zip)).map(z => ({
        label: z.label,
        data: grouped.get(z.zip)!.map(p => p.median_value),
        borderColor: z.color,
        backgroundColor: z.color + '18',
        borderWidth: 2,
        fill: false,
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 4,
      })),
    };
  });

  latestRedfin = computed(() => {
    const data = this.redfin();
    const latest = new Map<string, RedfinPoint>();
    for (const r of data) {
      const existing = latest.get(r.zip_code);
      if (!existing || r.period_begin > existing.period_begin) {
        latest.set(r.zip_code, r);
      }
    }
    return ['75206', '75214', '75238']
      .map(z => latest.get(z))
      .filter((r): r is RedfinPoint => !!r);
  });

  redfinTableRows = computed(() => {
    const data = this.latestRedfin();
    if (!data.length) return [];
    const byZip = new Map(data.map(r => [r.zip_code, r]));
    const zips = ['75206', '75214', '75238'];
    const fmt$ = (v: number | null | undefined) =>
      v != null ? '$' + Math.round(v).toLocaleString() : '—';
    return [
      {
        label: 'Median List Price',
        values: zips.map(z => fmt$(byZip.get(z)?.median_list_price)),
      },
      {
        label: 'Median Sale Price',
        values: zips.map(z => fmt$(byZip.get(z)?.median_sale_price)),
      },
      {
        label: 'Inventory',
        values: zips.map(z => byZip.get(z)?.inventory?.toString() ?? '—'),
      },
      {
        label: 'New Listings',
        values: zips.map(z => byZip.get(z)?.new_listings?.toString() ?? '—'),
      },
      {
        label: 'Days on Market',
        values: zips.map(z => {
          const v = byZip.get(z)?.days_on_market;
          return v != null ? v.toFixed(0) + ' days' : '—';
        }),
      },
      {
        label: 'Sale-to-List',
        values: zips.map(z => {
          const v = byZip.get(z)?.sale_to_list_ratio;
          return v != null ? (v * 100).toFixed(1) + '%' : '—';
        }),
      },
    ];
  });

  ngOnInit(): void {
    this.api.housePriceSummary().subscribe({
      next: data => { this.summary.set(data); this.loading.set(false); },
      error: ()   => this.loading.set(false),
    });
    this.loadZhvi();
    this.loadRedfin();
  }

  onHomeTypeChange(value: string): void {
    this.selectedHomeType.set(value);
    this.loadZhvi();
  }

  onMonthsChange(value: number): void {
    this.selectedMonths.set(value);
    this.loadZhvi();
    this.loadRedfin();
  }

  formatK(value: number): string {
    return (value / 1000).toFixed(0) + 'K';
  }

  private loadZhvi(): void {
    this.api.zhviTrend(this.selectedHomeType(), this.selectedMonths()).subscribe({
      next: data => this.zhvi.set(data),
      error: ()   => this.zhvi.set([]),
    });
  }

  private loadRedfin(): void {
    this.api.redfinMetrics(this.selectedMonths()).subscribe({
      next: data => this.redfin.set(data),
      error: ()   => this.redfin.set([]),
    });
  }
}

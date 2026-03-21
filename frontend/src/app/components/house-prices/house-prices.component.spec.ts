import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { of } from 'rxjs';

import { HousePricesComponent } from './house-prices.component';
import { ApiService } from '../../services/api.service';
import { HousePriceSummary, ZhviPoint, RedfinPoint } from '../../models/apartment.model';

const SUMMARY: HousePriceSummary[] = [
  {
    zip_code: '75206', display_name: 'M Streets', neighborhoods: null,
    zhvi_current: 600000, zhvi_month: '2026-02-28',
    median_list_price: null, median_sale_price: null,
    inventory: 12, days_on_market: 18, new_listings: null, redfin_week: null,
  },
  {
    zip_code: '75214', display_name: 'Lakewood', neighborhoods: null,
    zhvi_current: 820000, zhvi_month: '2026-02-28',
    median_list_price: null, median_sale_price: null,
    inventory: null, days_on_market: null, new_listings: null, redfin_week: null,
  },
];

const ZHVI: ZhviPoint[] = [
  { zip_code: '75206', month: '2026-02-28', median_value: 600000, home_type: 'all_middle_tier' },
  { zip_code: '75214', month: '2026-02-28', median_value: 820000, home_type: 'all_middle_tier' },
];

const REDFIN: RedfinPoint[] = [
  {
    zip_code: '75206', period_begin: '2026-03-10', period_end: '2026-03-16',
    median_sale_price: 580000, median_list_price: 610000,
    homes_sold: 8, new_listings: 14, inventory: 12,
    days_on_market: 18, sale_to_list_ratio: 0.98, median_ppsf: 310,
  },
];

const mockApi = {
  housePriceSummary: () => of(SUMMARY),
  zhviTrend:         () => of(ZHVI),
  redfinMetrics:     () => of(REDFIN),
};

async function setup() {
  await TestBed.configureTestingModule({
    imports: [HousePricesComponent],
    providers: [
      { provide: ApiService, useValue: mockApi },
      provideHttpClient(),
      provideHttpClientTesting(),
      provideAnimationsAsync(),
    ],
  }).compileComponents();

  const fixture   = TestBed.createComponent(HousePricesComponent);
  const component = fixture.componentInstance;
  fixture.detectChanges();
  return { fixture, component };
}

describe('HousePricesComponent', () => {

  it('creates successfully', async () => {
    const { component } = await setup();
    expect(component).toBeTruthy();
  });

  it('populates summary signal after ngOnInit', async () => {
    const { component } = await setup();
    expect(component.summary().length).toBe(2);
    expect(component.summary()[0].zip_code).toBe('75206');
  });

  it('loading is false after data loads', async () => {
    const { component } = await setup();
    expect(component.loading()).toBeFalse();
  });

  it('populates zhvi signal after ngOnInit', async () => {
    const { component } = await setup();
    expect(component.zhvi().length).toBe(2);
  });

  it('zhviChartData returns non-null when zhvi has data', async () => {
    const { component } = await setup();
    expect(component.zhviChartData()).not.toBeNull();
  });

  it('zhviChartData returns null when zhvi is empty', async () => {
    const { component } = await setup();
    component.zhvi.set([]);
    expect(component.zhviChartData()).toBeNull();
  });

  it('selectedHomeType defaults to all_middle_tier', async () => {
    const { component } = await setup();
    expect(component.selectedHomeType()).toBe('all_middle_tier');
  });

  it('selectedMonths defaults to 24', async () => {
    const { component } = await setup();
    expect(component.selectedMonths()).toBe(24);
  });

  it('renders app-affordability-calculator component', async () => {
    const { fixture } = await setup();
    expect(fixture.nativeElement.querySelector('app-affordability-calculator')).not.toBeNull();
  });

  it('redfinTableRows returns empty when redfin signal is empty', async () => {
    const { component } = await setup();
    component.redfin.set([]);
    expect(component.redfinTableRows().length).toBe(0);
  });

  it('redfinTableRows returns rows when redfin has data', async () => {
    const { component } = await setup();
    expect(component.redfinTableRows().length).toBeGreaterThan(0);
  });

  // ── formatK ────────────────────────────────────────────────────────────────

  it('formatK(1000) returns "1K"', async () => {
    const { component } = await setup();
    expect(component.formatK(1000)).toBe('1K');
  });

  it('formatK(594522) returns "595K"', async () => {
    const { component } = await setup();
    expect(component.formatK(594522)).toBe('595K');
  });

  it('formatK(1000000) returns "1000K"', async () => {
    const { component } = await setup();
    expect(component.formatK(1000000)).toBe('1000K');
  });

  // ── onHomeTypeChange / onMonthsChange ──────────────────────────────────────

  it('onHomeTypeChange updates selectedHomeType signal', async () => {
    const { component } = await setup();
    component.onHomeTypeChange('3bed');
    expect(component.selectedHomeType()).toBe('3bed');
  });

  it('onHomeTypeChange updates selectedHomeType to sfr_only', async () => {
    const { component } = await setup();
    component.onHomeTypeChange('sfr_only');
    expect(component.selectedHomeType()).toBe('sfr_only');
  });

  it('onMonthsChange updates selectedMonths signal', async () => {
    const { component } = await setup();
    component.onMonthsChange(12);
    expect(component.selectedMonths()).toBe(12);
  });

  it('onMonthsChange updates selectedMonths to 60', async () => {
    const { component } = await setup();
    component.onMonthsChange(60);
    expect(component.selectedMonths()).toBe(60);
  });

  // ── latestRedfin — picks latest per zip ───────────────────────────────────

  it('latestRedfin picks the most recent period_begin per zip', async () => {
    const { component } = await setup();
    component.redfin.set([
      { ...REDFIN[0], period_begin: '2026-02-01', median_sale_price: 560000, period_end: '2026-02-07',
        median_list_price: null, homes_sold: null, new_listings: null, inventory: null,
        days_on_market: null, sale_to_list_ratio: null, median_ppsf: null },
      { ...REDFIN[0], period_begin: '2026-03-10', median_sale_price: 580000, period_end: '2026-03-16',
        median_list_price: null, homes_sold: null, new_listings: null, inventory: null,
        days_on_market: null, sale_to_list_ratio: null, median_ppsf: null },
    ]);
    const latest = component.latestRedfin();
    expect(latest.length).toBe(1);
    expect(latest[0].median_sale_price).toBe(580000);
  });

  it('latestRedfin returns empty when redfin is empty', async () => {
    const { component } = await setup();
    component.redfin.set([]);
    expect(component.latestRedfin().length).toBe(0);
  });

  // ── zhviChartData structure ────────────────────────────────────────────────

  it('zhviChartData has one dataset per zip present in data', async () => {
    const { component } = await setup();
    const chart = component.zhviChartData()!;
    expect(chart.datasets.length).toBe(2); // ZHVI has data for 75206 and 75214
  });

  it('zhviChartData labels are formatted as MM/YY', async () => {
    const { component } = await setup();
    const chart = component.zhviChartData()!;
    expect(chart.labels[0]).toMatch(/^\d{2}\/\d{2}$/);
  });

  it('zhviChartData datasets have borderColor set', async () => {
    const { component } = await setup();
    const chart = component.zhviChartData()!;
    chart.datasets.forEach((ds: any) => {
      expect(ds.borderColor).toBeTruthy();
    });
  });
});

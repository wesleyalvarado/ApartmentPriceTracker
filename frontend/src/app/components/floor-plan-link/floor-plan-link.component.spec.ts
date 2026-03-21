import { TestBed } from '@angular/core/testing';
import { FloorPlanLinkComponent } from './floor-plan-link.component';
import { DisplayFloorPlan } from '../../models/apartment.model';

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

async function setup(fp: DisplayFloorPlan) {
  await TestBed.configureTestingModule({
    imports: [FloorPlanLinkComponent],
  }).compileComponents();

  const fixture = TestBed.createComponent(FloorPlanLinkComponent);
  fixture.componentInstance.fp = fp;
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance };
}

describe('FloorPlanLinkComponent', () => {

  describe('url getter', () => {
    it('returns null for unknown complex_id', async () => {
      const { component } = await setup(makeFp({ complex_id: 99 }));
      expect(component.url).toBeNull();
    });

    it('builds Camden URL without floor param when url_floor is null', async () => {
      const { component } = await setup(makeFp({ url_floor: null }));
      expect(component.url).toBe(
        'https://www.camdenliving.com/apartments/dallas-tx/camden-greenville/available-apartments/a1-villas-floor-plan'
      );
    });

    it('appends ?floor=N to Camden URL when url_floor is set', async () => {
      const { component } = await setup(makeFp({ url_floor: 2 }));
      expect(component.url).toBe(
        'https://www.camdenliving.com/apartments/dallas-tx/camden-greenville/available-apartments/a1-villas-floor-plan?floor=2'
      );
    });

    it('returns fixed SkyHouse URL regardless of slug or url_floor', async () => {
      const { component } = await setup(makeFp({ complex_id: 2, complex_name: 'SkyHouse Dallas', floorplan_slug: 'b', url_floor: null }));
      expect(component.url).toBe(
        'https://www.simpsonpropertygroup.com/apartments/dallas-texas/skyhouse-dallas-victory-park-downtown/apartment-floor-plans/#plan'
      );
    });

    it('returns same fixed SkyHouse URL for a different slug', async () => {
      const { component } = await setup(makeFp({ complex_id: 2, floorplan_slug: 'c2-c3' }));
      expect(component.url).toBe(
        'https://www.simpsonpropertygroup.com/apartments/dallas-texas/skyhouse-dallas-victory-park-downtown/apartment-floor-plans/#plan'
      );
    });
  });

  describe('template', () => {
    it('renders nothing when complex_id is unknown', async () => {
      const { fixture } = await setup(makeFp({ complex_id: 99 }));
      const anchor = fixture.nativeElement.querySelector('a');
      expect(anchor).toBeNull();
    });

    it('renders anchor with correct href for Camden with floor', async () => {
      const { fixture } = await setup(makeFp({ url_floor: 2 }));
      const anchor: HTMLAnchorElement = fixture.nativeElement.querySelector('a');
      expect(anchor).not.toBeNull();
      expect(anchor.href).toBe(
        'https://www.camdenliving.com/apartments/dallas-tx/camden-greenville/available-apartments/a1-villas-floor-plan?floor=2'
      );
    });

    it('opens link in new tab', async () => {
      const { fixture } = await setup(makeFp({ url_floor: 1 }));
      const anchor: HTMLAnchorElement = fixture.nativeElement.querySelector('a');
      expect(anchor.target).toBe('_blank');
      expect(anchor.rel).toContain('noopener');
    });
  });
});

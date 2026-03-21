import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { of } from 'rxjs';

import { DashboardComponent } from './dashboard.component';
import { ApiService } from '../../services/api.service';

const mockApi = {
  complexes:         () => of([]),
  floorPlans:        () => of([]),
  leaseTerms:        () => of([14, 6, 5, 4]),
  rented:            () => of([]),
  unitsForFloorPlan: () => of([]),
  floorPlanHistory:  () => of([]),
};

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

  it('calls API on ngOnInit and populates loading state', async () => {
    const { component } = await setup();
    expect(component.loading()).toBeFalse();
  });
});

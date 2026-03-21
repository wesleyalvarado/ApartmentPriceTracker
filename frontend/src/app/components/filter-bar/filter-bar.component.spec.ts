import { TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { FilterBarComponent } from './filter-bar.component';
import {
  BedroomOption, LeaseTermOption, ComplexOption,
  AvailabilityOption, StatusOption,
} from '../../services/dashboard-state.service';

const BEDROOM_OPTIONS: BedroomOption[] = [
  { label: 'All', value: null }, { label: 'Studio', value: 0 },
  { label: '1 BR', value: 1 },  { label: '2 BR', value: 2 },
];
const AVAIL_OPTIONS: AvailabilityOption[] = [
  { label: 'Any', value: null }, { label: 'Now', value: 0 },
  { label: '30 days', value: 30 },
];
const LEASE_OPTIONS: LeaseTermOption[] = [
  { label: '15 mo', value: 15 }, { label: '14 mo', value: 14 },
];
const STATUS_OPTIONS: StatusOption[] = [
  { label: 'Available', value: 'available' },
  { label: 'Rented',    value: 'rented' },
  { label: 'All',       value: 'all' },
];
const COMPLEX_OPTIONS_1: ComplexOption[] = [{ label: 'All', value: null }];
const COMPLEX_OPTIONS_3: ComplexOption[] = [
  { label: 'All', value: null },
  { label: 'Camden Greenville', value: 1 },
  { label: 'Camden Buckingham', value: 2 },
];

async function setup(overrides: {
  complexOptions?: ComplexOption[];
  planCount?: number;
} = {}) {
  await TestBed.configureTestingModule({
    imports: [FilterBarComponent],
    providers: [provideAnimationsAsync()],
  }).compileComponents();

  const fixture   = TestBed.createComponent(FilterBarComponent);
  const component = fixture.componentInstance;

  component.complexOptions     = overrides.complexOptions ?? COMPLEX_OPTIONS_1;
  component.bedroomOptions     = BEDROOM_OPTIONS;
  component.availabilityOptions = AVAIL_OPTIONS;
  component.leaseTermOptions   = LEASE_OPTIONS;
  component.statusOptions      = STATUS_OPTIONS;
  component.selectedComplexId  = null;
  component.selectedBedrooms   = null;
  component.selectedAvailability = null;
  component.selectedLeaseTerm  = 15;
  component.selectedStatus     = 'available';
  component.planCount          = overrides.planCount ?? 5;

  fixture.detectChanges();
  return { fixture, component };
}

describe('FilterBarComponent', () => {

  it('creates successfully', async () => {
    const { component } = await setup();
    expect(component).toBeTruthy();
  });

  it('shows count badge with correct text (plural)', async () => {
    const { fixture } = await setup({ planCount: 5 });
    const badge = fixture.nativeElement.querySelector('.filter-count-badge');
    expect(badge.textContent.trim()).toBe('5 floor plans');
  });

  it('shows count badge with singular text when planCount is 1', async () => {
    const { fixture } = await setup({ planCount: 1 });
    const badge = fixture.nativeElement.querySelector('.filter-count-badge');
    expect(badge.textContent.trim()).toBe('1 floor plan');
  });

  it('hides Property filter group when complexOptions has 2 or fewer entries', async () => {
    const { fixture } = await setup({ complexOptions: COMPLEX_OPTIONS_1 });
    const groups = fixture.nativeElement.querySelectorAll('.filter-group');
    // Only Bedrooms, Available From, Lease Term, Status — no Property
    expect(groups.length).toBe(4);
  });

  it('shows Property filter group when complexOptions has more than 2 entries', async () => {
    const { fixture } = await setup({ complexOptions: COMPLEX_OPTIONS_3 });
    const groups = fixture.nativeElement.querySelectorAll('.filter-group');
    // Property + Bedrooms + Available From + Lease Term + Status
    expect(groups.length).toBe(5);
  });

  it('emits bedroomChange when bedroom selection changes', async () => {
    const { component } = await setup();
    let emitted: number | null | undefined;
    component.bedroomChange.subscribe(v => emitted = v);
    component.bedroomChange.emit(1);
    expect(emitted).toBe(1);
  });

  it('emits availabilityChange when availability selection changes', async () => {
    const { component } = await setup();
    let emitted: number | null | undefined;
    component.availabilityChange.subscribe(v => emitted = v);
    component.availabilityChange.emit(30);
    expect(emitted).toBe(30);
  });

  it('emits leaseTermChange when lease term selection changes', async () => {
    const { component } = await setup();
    let emitted: number | undefined;
    component.leaseTermChange.subscribe(v => emitted = v);
    component.leaseTermChange.emit(14);
    expect(emitted).toBe(14);
  });

  it('emits statusChange when status selection changes', async () => {
    const { component } = await setup();
    let emitted: string | undefined;
    component.statusChange.subscribe(v => emitted = v);
    component.statusChange.emit('rented');
    expect(emitted).toBe('rented');
  });

  it('emits complexChange when complex selection changes', async () => {
    const { component } = await setup({ complexOptions: COMPLEX_OPTIONS_3 });
    let emitted: number | null | undefined;
    component.complexChange.subscribe(v => emitted = v);
    component.complexChange.emit(1);
    expect(emitted).toBe(1);
  });
});

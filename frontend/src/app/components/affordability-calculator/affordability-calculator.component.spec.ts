import { TestBed } from '@angular/core/testing';
import { AffordabilityCalculatorComponent } from './affordability-calculator.component';

async function setup() {
  await TestBed.configureTestingModule({
    imports: [AffordabilityCalculatorComponent],
  }).compileComponents();

  const fixture   = TestBed.createComponent(AffordabilityCalculatorComponent);
  const component = fixture.componentInstance;
  fixture.detectChanges();
  return { fixture, component };
}

describe('AffordabilityCalculatorComponent', () => {

  it('creates successfully', async () => {
    const { component } = await setup();
    expect(component).toBeTruthy();
  });

  // ── signal defaults ────────────────────────────────────────────────────────

  it('maxMonthly defaults to 3500', async () => {
    const { component } = await setup();
    expect(component.maxMonthly()).toBe(3500);
  });

  it('mortgageRate defaults to 6.3', async () => {
    const { component } = await setup();
    expect(component.mortgageRate()).toBe(6.3);
  });

  it('downPct defaults to 20', async () => {
    const { component } = await setup();
    expect(component.downPct()).toBe(20);
  });

  // ── affordability computed ─────────────────────────────────────────────────

  it('affordability returns a result with valid defaults', async () => {
    const { component } = await setup();
    expect(component.affordability()).not.toBeNull();
  });

  it('affordability maxPrice is positive with valid inputs', async () => {
    const { component } = await setup();
    expect(component.affordability()!.maxPrice).toBeGreaterThan(0);
  });

  it('affordability returns null when budget equals insurance cost', async () => {
    const { component } = await setup();
    component.maxMonthly.set(component.insMonthly()); // use signal value, not hardcoded
    expect(component.affordability()).toBeNull();
  });

  it('affordability returns null when budget is below insurance cost', async () => {
    const { component } = await setup();
    component.maxMonthly.set(100);
    expect(component.affordability()).toBeNull();
  });

  it('affordability returns null when rate is 0', async () => {
    const { component } = await setup();
    component.mortgageRate.set(0);
    expect(component.affordability()).toBeNull();
  });

  it('affordability returns null when down is 100', async () => {
    const { component } = await setup();
    component.downPct.set(100);
    expect(component.affordability()).toBeNull();
  });

  it('affordability maxPrice increases when budget increases', async () => {
    const { component } = await setup();
    const low = component.affordability()!.maxPrice;
    component.maxMonthly.set(5000);
    expect(component.affordability()!.maxPrice).toBeGreaterThan(low);
  });

  it('affordability maxPrice decreases when rate increases', async () => {
    const { component } = await setup();
    component.mortgageRate.set(5);
    const low = component.affordability()!.maxPrice;
    component.mortgageRate.set(8);
    expect(component.affordability()!.maxPrice).toBeLessThan(low);
  });

  it('affordability downAmount equals maxPrice * downPct / 100', async () => {
    const { component } = await setup();
    const a = component.affordability()!;
    expect(a.downAmount).toBeCloseTo(a.maxPrice * 0.2, -2);
  });

  it('affordability loanAmount equals maxPrice minus downAmount', async () => {
    const { component } = await setup();
    const a = component.affordability()!;
    expect(a.loanAmount).toBeCloseTo(a.maxPrice - a.downAmount, -1);
  });

  it('insMonthly defaults to 175', async () => {
    const { component } = await setup();
    expect(component.insMonthly()).toBe(175);
  });

  it('affordability insMonthly reflects the signal value', async () => {
    const { component } = await setup();
    expect(component.affordability()!.insMonthly).toBe(175);
  });

  it('affordability insMonthly updates when signal changes', async () => {
    const { component } = await setup();
    component.insMonthly.set(250);
    expect(component.affordability()!.insMonthly).toBe(250);
  });

  it('higher insurance reduces max purchase price', async () => {
    const { component } = await setup();
    const low = component.affordability()!.maxPrice;
    component.insMonthly.set(400);
    expect(component.affordability()!.maxPrice).toBeLessThan(low);
  });

  it('affordability returns null when insurance equals budget', async () => {
    const { component } = await setup();
    component.maxMonthly.set(300);
    component.insMonthly.set(300);
    expect(component.affordability()).toBeNull();
  });

  it('affordability monthlyPI + monthlyTax + insMonthly roughly equals budget', async () => {
    const { component } = await setup();
    const a = component.affordability()!;
    const total = a.monthlyPI + a.monthlyTax + a.insMonthly;
    // Should be within $5 of the target budget (rounding)
    expect(Math.abs(total - component.maxMonthly())).toBeLessThan(5);
  });

  // ── closing costs ──────────────────────────────────────────────────────────

  it('closingCostPct defaults to 3', async () => {
    const { component } = await setup();
    expect(component.closingCostPct()).toBe(3);
  });

  it('closingCosts equals maxPrice * closingCostPct / 100', async () => {
    const { component } = await setup();
    const a = component.affordability()!;
    expect(a.closingCosts).toBeCloseTo(a.maxPrice * 0.03, -2);
  });

  it('closingCosts updates when closingCostPct changes', async () => {
    const { component } = await setup();
    const low = component.affordability()!.closingCosts;
    component.closingCostPct.set(5);
    expect(component.affordability()!.closingCosts).toBeGreaterThan(low);
  });

  it('closingCosts is 0 when closingCostPct is 0', async () => {
    const { component } = await setup();
    component.closingCostPct.set(0);
    expect(component.affordability()!.closingCosts).toBe(0);
  });

  it('renders the closing costs line in the result', async () => {
    const { fixture } = await setup();
    const closing = fixture.nativeElement.querySelector('.calc-closing');
    expect(closing).not.toBeNull();
    expect(closing.textContent).toContain('closing costs');
  });

  it('total monthly cost still matches budget when insurance is changed', async () => {
    const { component } = await setup();
    component.insMonthly.set(300);
    const a = component.affordability()!;
    const total = a.monthlyPI + a.monthlyTax + a.insMonthly;
    expect(Math.abs(total - component.maxMonthly())).toBeLessThan(5);
  });

  // ── template ───────────────────────────────────────────────────────────────

  it('renders the calc-card element', async () => {
    const { fixture } = await setup();
    expect(fixture.nativeElement.querySelector('.calc-card')).not.toBeNull();
  });

  it('renders calc-result section when affordability is not null', async () => {
    const { fixture } = await setup();
    expect(fixture.nativeElement.querySelector('.calc-result')).not.toBeNull();
  });

  it('does not render calc-result when budget is too low', async () => {
    const { fixture, component } = await setup();
    component.maxMonthly.set(100);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.calc-result')).toBeNull();
  });

  it('renders five input fields', async () => {
    const { fixture } = await setup();
    const inputs = fixture.nativeElement.querySelectorAll('input[type="number"]');
    expect(inputs.length).toBe(5);
  });

  it('renders the disclaimer note', async () => {
    const { fixture } = await setup();
    const note = fixture.nativeElement.querySelector('.calc-note');
    expect(note.textContent).toContain('30yr fixed');
    expect(note.textContent).toContain('1.85%');
  });
});

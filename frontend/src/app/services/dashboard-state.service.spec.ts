import { TestBed } from '@angular/core/testing';
import { DashboardStateService } from './dashboard-state.service';

function setup() {
  TestBed.configureTestingModule({});
  return TestBed.inject(DashboardStateService);
}

describe('DashboardStateService', () => {

  describe('bedroomLabel()', () => {
    it('returns Studio for 0', () => expect(setup().bedroomLabel(0)).toBe('Studio'));
    it('returns 1 Bedroom for 1', () => expect(setup().bedroomLabel(1)).toBe('1 Bedroom'));
    it('returns N Bedrooms for N > 1', () => expect(setup().bedroomLabel(2)).toBe('2 Bedrooms'));
  });

  describe('formatDate()', () => {
    it('returns — for null', () => expect(setup().formatDate(null)).toBe('—'));
    it('returns Available Now for past dates', () => expect(setup().formatDate('2020-01-01')).toBe('Available Now'));
    it('returns formatted date for future dates', () => {
      const result = setup().formatDate('2099-06-15');
      expect(result).toContain('Jun');
      expect(result).toContain('15');
    });
  });
});

import { TestBed } from '@angular/core/testing';
import { DashboardStateService } from './dashboard-state.service';

function setup() {
  TestBed.configureTestingModule({});
  return TestBed.inject(DashboardStateService);
}

describe('DashboardStateService', () => {

  describe('bedroomLabel()', () => {
    it('returns Studio for 0',         () => expect(setup().bedroomLabel(0)).toBe('Studio'));
    it('returns 1 Bedroom for 1',      () => expect(setup().bedroomLabel(1)).toBe('1 Bedroom'));
    it('returns 2 Bedrooms for 2',     () => expect(setup().bedroomLabel(2)).toBe('2 Bedrooms'));
    it('returns 3 Bedrooms for 3',     () => expect(setup().bedroomLabel(3)).toBe('3 Bedrooms'));
    it('returns 4 Bedrooms for 4',     () => expect(setup().bedroomLabel(4)).toBe('4 Bedrooms'));
    it('uses plural for all N > 1',    () => expect(setup().bedroomLabel(5)).toContain('Bedrooms'));
    it('never returns plural for 1',   () => expect(setup().bedroomLabel(1)).not.toContain('Bedrooms'));
  });

  describe('formatDate()', () => {
    it('returns — for null',                  () => expect(setup().formatDate(null)).toBe('—'));
    it('returns Available Now for past dates', () => expect(setup().formatDate('2020-01-01')).toBe('Available Now'));
    it('returns Available Now for today',     () => {
      const today = new Date().toISOString().slice(0, 10);
      expect(setup().formatDate(today)).toBe('Available Now');
    });
    it('returns formatted date for future dates', () => {
      const result = setup().formatDate('2099-06-15');
      expect(result).toContain('Jun');
      expect(result).toContain('15');
    });
    it('includes year for far-future dates', () => {
      const result = setup().formatDate('2099-06-15');
      expect(result).toContain('2099');
    });
    it('returns Available Now for dates far in the past', () => {
      expect(setup().formatDate('2000-01-01')).toBe('Available Now');
    });
  });
});

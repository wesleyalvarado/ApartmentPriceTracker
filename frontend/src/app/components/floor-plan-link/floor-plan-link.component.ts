import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DisplayFloorPlan } from '../../models/apartment.model';

// Complexes where each floor plan has its own slug-based URL
const COMPLEX_BASE_URLS: Record<number, string> = {
  1: 'https://www.camdenliving.com/apartments/dallas-tx/camden-greenville/available-apartments',
};

// Complexes with a single fixed URL for all floor plans
const COMPLEX_STATIC_URLS: Record<number, string> = {
  2: 'https://www.simpsonpropertygroup.com/apartments/dallas-texas/skyhouse-dallas-victory-park-downtown/apartment-floor-plans/#plan',
};

@Component({
  selector: 'app-floor-plan-link',
  standalone: true,
  imports: [CommonModule],
  styles: [`
    a {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: .72rem;
      font-weight: 600;
      color: var(--camden-muted);
      text-decoration: none;
      opacity: .7;
      transition: opacity .15s;

      &:hover { opacity: 1; }
      .pi { font-size: .7rem; }
    }
  `],
  template: `
    @if (url) {
      <a [href]="url" target="_blank" rel="noopener noreferrer" (click)="$event.stopPropagation()">
        <i class="pi pi-external-link"></i>
        View
      </a>
    }
  `,
})
export class FloorPlanLinkComponent {
  @Input({ required: true }) fp!: DisplayFloorPlan;

  get url(): string | null {
    const staticUrl = COMPLEX_STATIC_URLS[this.fp.complex_id];
    if (staticUrl) return staticUrl;

    const base = COMPLEX_BASE_URLS[this.fp.complex_id];
    if (!base) return null;
    const floor = this.fp.url_floor != null ? `?floor=${this.fp.url_floor}` : '';
    return `${base}/${this.fp.floorplan_slug}${floor}`;
  }
}

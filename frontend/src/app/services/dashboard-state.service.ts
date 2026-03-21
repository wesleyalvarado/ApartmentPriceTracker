import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class DashboardStateService {

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

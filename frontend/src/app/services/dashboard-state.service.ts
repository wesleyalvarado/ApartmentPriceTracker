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
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (d <= today) return 'Available Now';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }
}

import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TooltipModule } from 'primeng/tooltip';
import { PriceDrop } from '../../models/apartment.model';

@Component({
  selector: 'app-price-drop-badge',
  standalone: true,
  imports: [CommonModule, TooltipModule],
  template: `
    @if (drop) {
      <span
        [class]="'price-change-badge price-change-badge--' + drop.direction"
        [pTooltip]="tooltipText()"
        tooltipPosition="top"
      >
        <i [class]="'pi ' + (drop.direction === 'drop' ? 'pi-arrow-down' : 'pi-arrow-up')"></i>
        \${{ drop.cumulative_drop | number }}&nbsp;({{ drop.drop_pct }}%)
      </span>
    }
  `,
  styles: [`
    .price-change-badge {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      padding: 2px 8px;
      border-radius: 99px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.02em;
      white-space: nowrap;
      cursor: default;

      .pi { font-size: 10px; }

      &--drop {
        background: #fee2e2;
        color: #991b1b;
        border: 1px solid #fca5a5;
      }

      &--increase {
        background: #fff7ed;
        color: #9a3412;
        border: 1px solid #fdba74;
      }
    }
  `],
})
export class PriceDropBadgeComponent {
  @Input({ required: true }) drop!: PriceDrop | null;

  tooltipText(): string {
    if (!this.drop) return '';
    const [, month, day] = this.drop.first_seen.split('-');
    const arrow = this.drop.direction === 'drop' ? '↓' : '↑';
    return `Unit ${this.drop.best_unit_id}: was $${this.drop.baseline_min.toLocaleString()} on ${month}/${day} ${arrow} now $${this.drop.current_min.toLocaleString()}`;
  }
}

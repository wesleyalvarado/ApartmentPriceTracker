import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { SkeletonModule } from 'primeng/skeleton';
import { ChipModule } from 'primeng/chip';
import { DividerModule } from 'primeng/divider';
import { ChartModule } from 'primeng/chart';

import { DashboardStateService } from '../../services/dashboard-state.service';
import { DisplayFloorPlan, DisplayUnit, StatusValue, PriceDrop } from '../../models/apartment.model';
import { FloorPlanLinkComponent } from '../floor-plan-link/floor-plan-link.component';
import { PriceDropBadgeComponent } from '../price-drop-badge/price-drop-badge.component';

@Component({
  selector: 'app-floor-plan-card',
  standalone: true,
  imports: [
    CommonModule,
    CardModule, TableModule, TagModule, SkeletonModule,
    ChipModule, DividerModule, ChartModule,
    FloorPlanLinkComponent, PriceDropBadgeComponent,
  ],
  styles: [`
    :host { display: flex; flex-direction: column; }
    .card-wrapper { display: flex; flex-direction: column; gap: 0; }

    :host ::ng-deep .fp-card {
      border: 1px solid var(--camden-border); border-radius: 12px !important;
      overflow: hidden; transition: box-shadow .2s, transform .15s; cursor: pointer;
    }
    :host ::ng-deep .fp-card:hover {
      box-shadow: 0 4px 20px rgba(43,87,65,.15) !important; transform: translateY(-2px);
    }
    :host ::ng-deep .fp-card--expanded {
      border-bottom-left-radius: 0 !important; border-bottom-right-radius: 0 !important;
      border-bottom-color: var(--camden-green) !important;
      box-shadow: 0 4px 20px rgba(43,87,65,.15) !important;
    }
    :host ::ng-deep .fp-card .p-card-body { padding: 0; }

    .card-header-band {
      background: var(--camden-green-pale); padding: .75rem 1.25rem;
      display: flex; align-items: center; justify-content: space-between;
      border-bottom: 1px solid var(--camden-border);
    }
    .card-header-left { display: flex; flex-direction: column; gap: 3px; }
    .card-header-right { display: flex; align-items: center; gap: .5rem; }
    .card-plan-name { font-weight: 700; font-size: 1rem; color: var(--camden-green); }
    .complex-badge {
      font-size: .7rem; font-weight: 600; color: var(--camden-muted);
      text-transform: uppercase; letter-spacing: .05em;
    }

    .card-body { padding: 1.25rem; }
    .card-price { font-size: 2rem; font-weight: 800; color: var(--camden-green); line-height: 1; }
    .card-price-label { font-size: .75rem; color: var(--camden-muted); margin-bottom: .75rem; }
    .card-specs {
      display: flex; flex-wrap: wrap; gap: .6rem;
      font-size: .82rem; color: var(--camden-text); margin-bottom: .6rem;
    }
    .card-specs span {
      display: flex; align-items: center; gap: 4px;
      background: var(--camden-green-pale); padding: 3px 8px; border-radius: 20px;
    }
    .card-specs span .pi { font-size: .75rem; color: var(--camden-green); }
    .card-avail {
      font-size: .8rem; color: var(--camden-muted);
      display: flex; align-items: center; gap: 5px; margin-top: .4rem;
    }
    .card-avail .pi { font-size: .75rem; }
    .card-tags { display: flex; gap: .5rem; margin-top: .6rem; flex-wrap: wrap; }
    :host ::ng-deep .tag-chip .p-chip {
      font-size: .72rem; background: var(--camden-gold); color: white;
      padding: 2px 8px; border-radius: 20px;
    }
    .card-footer {
      display: flex; align-items: center; justify-content: space-between;
      padding: .6rem 1.25rem; font-size: .8rem; color: var(--camden-green);
      border-top: 1px solid var(--camden-border); font-weight: 600;
      background: var(--camden-green-pale);
    }

    .unit-panel {
      background: var(--camden-surface); border: 1px solid var(--camden-green);
      border-top: none; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;
      padding: 1.25rem; box-shadow: 0 4px 20px rgba(43,87,65,.12);
    }
    .section-label {
      font-size: .8rem; font-weight: 700; color: var(--camden-green);
      text-transform: uppercase; letter-spacing: .06em;
      display: flex; align-items: center; gap: 6px; margin-bottom: .75rem;
    }
    .chart-section { margin-bottom: 1rem; }
    .chart-container { height: 160px; }
    .chart-placeholder {
      font-size: .82rem; color: var(--camden-muted);
      display: flex; align-items: center; gap: 6px;
      padding: .75rem; background: var(--camden-green-pale);
      border-radius: 8px; margin-bottom: 1rem;
    }

    .floorplan-image-section { margin-bottom: 1rem; }
    .floorplan-img {
      display: block; max-width: 100%; max-height: 280px; object-fit: contain;
      border-radius: 8px; background: var(--camden-green-pale); padding: .5rem;
    }

    .unit-id-cell { font-weight: 600; }
    .unit-badge {
      background: var(--camden-green-pale); color: var(--camden-green);
      padding: 2px 10px; border-radius: 20px; font-size: .82rem; font-weight: 700;
    }
    .price-cell { font-weight: 700; color: var(--camden-green); font-size: 1rem; }
    .floor-cell { color: var(--camden-muted); font-size: .85rem; }

    .unit-row--rented td { opacity: .6; }
    .unit-badge--rented { background: #f3f4f6; color: #6b7280; }
    .price-cell--rented { font-weight: 700; color: var(--camden-muted); font-size: 1rem; }
    .rented-label {
      font-size: .8rem; color: var(--camden-muted);
      display: flex; align-items: center; gap: .35rem;
    }
    .rented-label .pi { font-size: .75rem; }
  `],
  template: `
    <div class="card-wrapper">
      <p-card
        [styleClass]="'fp-card ' + (isExpanded ? 'fp-card--expanded' : '')"
        (click)="toggleRequested.emit(fp)"
      >
        <ng-template #header>
          <div class="card-header-band">
            <div class="card-header-left">
              <span class="card-plan-name">{{ fp.floorplan_name }}</span>
              @if (showComplexBadge) {
                <span class="complex-badge">{{ fp.complex_name }}</span>
              }
              <app-floor-plan-link [fp]="fp" />
            </div>
            <div class="card-header-right">
              <app-price-drop-badge [drop]="priceDrop" />
              <p-tag
                [value]="fp.display_units + (fp.display_units === 1 ? ' unit' : ' units')"
                severity="success"
                [rounded]="true"
              />
            </div>
          </div>
        </ng-template>

        <div class="card-body">
          <div class="card-price">\${{ fp.display_min | number }}</div>
          <div class="card-price-label">/ mo</div>

          <div class="card-specs">
            <span>
              <i class="pi pi-home"></i>
              {{ bedroomLabel(fp.bedrooms) }}
            </span>
            <span>
              <i class="pi pi-droplet"></i>
              {{ fp.bathrooms }} Bath{{ fp.bathrooms !== 1 ? 's' : '' }}
            </span>
            <span>
              <i class="pi pi-expand"></i>
              {{ fp.sqft | number }} sqft
            </span>
          </div>

          @if (fp.earliest_available) {
            <div class="card-avail">
              <i class="pi pi-calendar"></i>
              Available {{ formatDate(fp.earliest_available) }}
            </div>
          }

          @if (fp.special_tags) {
            <div class="card-tags">
              @for (tag of fp.special_tags.split(','); track tag) {
                <p-chip [label]="tag.trim()" styleClass="tag-chip" />
              }
            </div>
          }
        </div>

        <ng-template #footer>
          <div class="card-footer">
            <span>{{ isExpanded ? 'Hide units' : 'View all units' }}</span>
            <i class="pi"
               [class.pi-chevron-down]="!isExpanded"
               [class.pi-chevron-up]="isExpanded"></i>
          </div>
        </ng-template>
      </p-card>

      <!-- Expanded unit panel -->
      @if (isExpanded) {
        <div class="unit-panel" (click)="$event.stopPropagation()">

          <!-- Price history chart -->
          @if (chartData) {
            <div class="chart-section">
              <div class="section-label">
                <i class="pi pi-chart-line"></i> Price History
              </div>
              <div class="chart-container">
                <p-chart type="line" [data]="chartData" [options]="chartOptions" height="160px" />
              </div>
            </div>
            <p-divider />
          } @else {
            <div class="chart-placeholder">
              <i class="pi pi-info-circle"></i>
              Price history chart will appear after multiple scrape runs.
            </div>
          }

          <!-- Floor plan image -->
          @if (fp.image_url) {
            <div class="floorplan-image-section">
              <div class="section-label">
                <i class="pi pi-image"></i> Floor Plan Layout
              </div>
              <img [src]="fp.image_url" alt="{{ fp.floorplan_name }} layout" class="floorplan-img" />
            </div>
            <p-divider />
          }

          <!-- Units table -->
          <div class="section-label">
            <i class="pi pi-list"></i> Available Units
          </div>

          @if (loadingUnits) {
            <p-skeleton height="120px" />
          } @else {
            <p-table
              [value]="expandedUnits"
              [tableStyle]="{'min-width': '100%'}"
              styleClass="p-datatable-sm"
            >
              <ng-template #header>
                <tr>
                  <th>Unit</th>
                  <th>Floor</th>
                  <th>Price/mo</th>
                  <th>Date</th>
                </tr>
              </ng-template>
              <ng-template #body let-unit>
                <tr [class.unit-row--rented]="unit.status === 'rented'">
                  <td class="unit-id-cell">
                    <span class="unit-badge" [class.unit-badge--rented]="unit.status === 'rented'">{{ unit.unit_id }}</span>
                  </td>
                  <td class="floor-cell">{{ unit.floor ?? '—' }}</td>
                  <td [class.price-cell]="unit.status === 'available'" [class.price-cell--rented]="unit.status === 'rented'">
                    \${{ unit.price | number }}
                  </td>
                  <td>
                    @if (unit.status === 'rented') {
                      <span class="rented-label">
                        <i class="pi pi-lock"></i>
                        Rented · {{ unit.last_seen | date:'MMM d' }}
                      </span>
                    } @else {
                      {{ formatDate(unit.available_date) }}
                    }
                  </td>
                </tr>
              </ng-template>
            </p-table>
          }
        </div>
      }
    </div>
  `,
})
export class FloorPlanCardComponent {
  private state = inject(DashboardStateService);

  @Input({ required: true }) fp!: DisplayFloorPlan;
  @Input({ required: true }) isExpanded!: boolean;
  @Input({ required: true }) loadingUnits!: boolean;
  @Input({ required: true }) expandedUnits!: DisplayUnit[];
  @Input({ required: true }) chartData!: any;
  @Input({ required: true }) chartOptions!: any;
  @Input({ required: true }) showComplexBadge!: boolean;
  @Input({ required: true }) selectedStatus!: StatusValue;
  @Input() priceDrop: PriceDrop | null = null;

  @Output() toggleRequested = new EventEmitter<DisplayFloorPlan>();

  bedroomLabel(n: number)       { return this.state.bedroomLabel(n); }
  formatDate(iso: string | null) { return this.state.formatDate(iso); }
}

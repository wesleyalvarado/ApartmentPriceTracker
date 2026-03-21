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
import { DisplayFloorPlan, DisplayUnit, StatusValue } from '../../models/apartment.model';

@Component({
  selector: 'app-floor-plan-card',
  standalone: true,
  imports: [
    CommonModule,
    CardModule, TableModule, TagModule, SkeletonModule,
    ChipModule, DividerModule, ChartModule,
  ],
  templateUrl: './floor-plan-card.component.html',
  styleUrl: './floor-plan-card.component.scss',
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

  @Output() toggleRequested = new EventEmitter<DisplayFloorPlan>();

  // Delegate formatting helpers to the state service
  bedroomLabel(n: number)          { return this.state.bedroomLabel(n); }
  formatDate(iso: string | null)    { return this.state.formatDate(iso); }
}

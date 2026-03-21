import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { SkeletonModule } from 'primeng/skeleton';

import { DashboardStateService } from '../../services/dashboard-state.service';
import { FloorPlanCardComponent } from '../floor-plan-card/floor-plan-card.component';
import { FilterBarComponent } from '../filter-bar/filter-bar.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, SkeletonModule, FloorPlanCardComponent, FilterBarComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  state = inject(DashboardStateService);
  ngOnInit() { this.state.initialize(); }
}

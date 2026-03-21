import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { SelectButtonModule } from 'primeng/selectbutton';

import {
  StatusValue,
  BedroomOption, LeaseTermOption, ComplexOption,
  AvailabilityOption, StatusOption,
} from '../../models/apartment.model';

@Component({
  selector: 'app-filter-bar',
  standalone: true,
  imports: [CommonModule, FormsModule, SelectButtonModule],
  styleUrl: './filter-bar.component.scss',
  template: `
    <div class="filters-panel">
      <div class="filters-body">

        @if (complexOptions.length > 2) {
          <div class="filter-group">
            <span class="filter-label">Property</span>
            <p-selectbutton
              [options]="complexOptions"
              [ngModel]="selectedComplexId"
              (ngModelChange)="complexChange.emit($event)"
              [ngModelOptions]="{standalone: true}"
              optionLabel="label"
              optionValue="value"
            />
          </div>
        }

        <div class="filter-group">
          <span class="filter-label">Bedrooms</span>
          <p-selectbutton
            [options]="bedroomOptions"
            [ngModel]="selectedBedrooms"
            (ngModelChange)="bedroomChange.emit($event)"
            [ngModelOptions]="{standalone: true}"
            optionLabel="label"
            optionValue="value"
          />
        </div>

        <div class="filter-group">
          <span class="filter-label">Available From</span>
          <p-selectbutton
            [options]="availabilityOptions"
            [ngModel]="selectedAvailability"
            (ngModelChange)="availabilityChange.emit($event)"
            [ngModelOptions]="{standalone: true}"
            optionLabel="label"
            optionValue="value"
          />
        </div>

        <div class="filter-group">
          <span class="filter-label">Lease Term</span>
          <p-selectbutton
            [options]="leaseTermOptions"
            [ngModel]="selectedLeaseTerm"
            (ngModelChange)="leaseTermChange.emit($event)"
            [ngModelOptions]="{standalone: true}"
            optionLabel="label"
            optionValue="value"
          />
        </div>

        <div class="filter-group">
          <span class="filter-label">Status</span>
          <p-selectbutton
            [options]="statusOptions"
            [ngModel]="selectedStatus"
            (ngModelChange)="statusChange.emit($event)"
            [ngModelOptions]="{standalone: true}"
            optionLabel="label"
            optionValue="value"
          />
        </div>

      </div>
      <div class="filter-count-badge">
        {{ planCount }} floor plan{{ planCount !== 1 ? 's' : '' }}
      </div>
    </div>
  `,
})
export class FilterBarComponent {
  @Input({ required: true }) complexOptions!: ComplexOption[];
  @Input({ required: true }) bedroomOptions!: BedroomOption[];
  @Input({ required: true }) availabilityOptions!: AvailabilityOption[];
  @Input({ required: true }) leaseTermOptions!: LeaseTermOption[];
  @Input({ required: true }) statusOptions!: StatusOption[];

  @Input({ required: true }) selectedComplexId!: number | null;
  @Input({ required: true }) selectedBedrooms!: number | null;
  @Input({ required: true }) selectedAvailability!: number | null;
  @Input({ required: true }) selectedLeaseTerm!: number;
  @Input({ required: true }) selectedStatus!: StatusValue;

  @Input({ required: true }) planCount!: number;

  @Output() complexChange      = new EventEmitter<number | null>();
  @Output() bedroomChange      = new EventEmitter<number | null>();
  @Output() availabilityChange = new EventEmitter<number | null>();
  @Output() leaseTermChange    = new EventEmitter<number>();
  @Output() statusChange       = new EventEmitter<StatusValue>();
}

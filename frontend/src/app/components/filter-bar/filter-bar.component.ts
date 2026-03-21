import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { SelectButtonModule } from 'primeng/selectbutton';

import {
  BedroomOption, LeaseTermOption, ComplexOption,
  AvailabilityOption, StatusOption,
} from '../../services/dashboard-state.service';
import { StatusValue } from '../../models/apartment.model';

@Component({
  selector: 'app-filter-bar',
  standalone: true,
  imports: [CommonModule, FormsModule, SelectButtonModule],
  templateUrl: './filter-bar.component.html',
  styleUrl: './filter-bar.component.scss',
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

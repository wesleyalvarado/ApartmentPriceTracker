import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { HousePricesComponent } from './components/house-prices/house-prices.component';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'house-prices', component: HousePricesComponent },
  { path: '**', redirectTo: '' },
];

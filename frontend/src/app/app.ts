import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  styles: [`
    .app-nav {
      position: sticky;
      top: 0;
      z-index: 200;
      background: var(--camden-surface);
      border-bottom: 1px solid var(--camden-border);
      box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }
    .app-nav-inner {
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      padding: 0 1.5rem;
      gap: 0;
    }
    .nav-tab {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: .75rem 1rem;
      font-size: .875rem;
      font-weight: 500;
      color: var(--camden-muted);
      text-decoration: none;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
      transition: color .15s, border-color .15s;
      cursor: pointer;
    }
    .nav-tab:hover {
      color: var(--camden-green);
    }
    .nav-tab.active {
      color: var(--camden-green);
      border-bottom-color: var(--camden-green);
      font-weight: 600;
    }
  `],
  template: `
    <nav class="app-nav">
      <div class="app-nav-inner">
        <a class="nav-tab"
           routerLink="/"
           routerLinkActive="active"
           [routerLinkActiveOptions]="{exact: true}">
          <i class="pi pi-building"></i> Apartments
        </a>
        <a class="nav-tab"
           routerLink="/house-prices"
           routerLinkActive="active">
          <i class="pi pi-home"></i> House Prices
        </a>
      </div>
    </nav>
    <router-outlet />
  `,
})
export class App {}

import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-affordability-calculator',
  standalone: true,
  imports: [CommonModule],
  styles: [`
    .calc-card {
      background: var(--camden-surface);
      border: 1px solid var(--camden-border);
      border-radius: 12px;
      padding: 1.25rem;
      box-shadow: 0 1px 4px rgba(0,0,0,.06);
      min-width: 0;
    }

    .section-label {
      font-size: .75rem;
      font-weight: 600;
      color: var(--camden-muted);
      text-transform: uppercase;
      letter-spacing: .06em;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .calc-body {
      display: flex;
      flex-direction: column;
      gap: .75rem;
    }

    .calc-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .5rem;

      label {
        font-size: .825rem;
        font-weight: 500;
        color: var(--camden-text);
        flex-shrink: 0;
      }

      input {
        width: 100px;
        padding: .35rem .6rem;
        border: 1px solid var(--camden-border);
        border-radius: 6px;
        font-size: .875rem;
        color: var(--camden-text);
        background: var(--camden-surface);
        text-align: right;

        &:focus {
          outline: none;
          border-color: var(--camden-green);
        }
      }
    }

    .calc-input-wrap {
      display: flex;
      align-items: center;
      border: 1px solid var(--camden-border);
      border-radius: 6px;
      overflow: hidden;

      span {
        padding: .35rem .5rem;
        background: var(--camden-green-pale);
        font-size: .875rem;
        color: var(--camden-green);
        font-weight: 600;
        border-right: 1px solid var(--camden-border);
      }

      input {
        width: 80px;
        border: none;
        border-radius: 0;
        padding-right: .5rem;

        &:focus { outline: none; border-color: transparent; }
      }
    }

    .calc-result {
      background: var(--camden-green-pale);
      border: 1px solid var(--camden-border);
      border-radius: 8px;
      padding: 1rem;
      text-align: center;
      margin-top: .25rem;
    }

    .calc-max-price {
      font-size: 1.75rem;
      font-weight: 800;
      color: var(--camden-green);
      line-height: 1;
    }

    .calc-max-label {
      font-size: .72rem;
      color: var(--camden-muted);
      text-transform: uppercase;
      letter-spacing: .05em;
      margin-top: 4px;
    }

    .calc-breakdown {
      display: flex;
      gap: .75rem;
      justify-content: center;
      font-size: .8rem;
      color: var(--camden-text);
      margin-top: .5rem;
      flex-wrap: wrap;
    }

    .calc-down {
      font-size: .78rem;
      color: var(--camden-muted);
      margin-top: .35rem;
    }

    .calc-closing {
      font-size: .78rem;
      color: var(--camden-muted);
      margin-top: .2rem;
      border-top: 1px dashed var(--camden-border);
      padding-top: .35rem;
    }

    .calc-note {
      font-size: .72rem;
      color: var(--camden-muted);
      text-align: center;
      border-top: 1px solid var(--camden-border);
      padding-top: .625rem;
      margin-top: .25rem;
    }
  `],
  template: `
    <div class="calc-card">
      <div class="section-label"><i class="pi pi-calculator"></i> Affordability Calculator</div>
      <div class="calc-body">
        <div class="calc-row">
          <label>Monthly budget</label>
          <div class="calc-input-wrap">
            <span>$</span>
            <input type="number"
                   [value]="maxMonthly()"
                   (input)="maxMonthly.set(+$any($event.target).value)"
                   min="1000" max="10000" step="100" />
          </div>
        </div>
        <div class="calc-row">
          <label>Rate (%)</label>
          <input type="number"
                 [value]="mortgageRate()"
                 (input)="mortgageRate.set(+$any($event.target).value)"
                 min="2" max="12" step="0.1" />
        </div>
        <div class="calc-row">
          <label>Down (%)</label>
          <input type="number"
                 [value]="downPct()"
                 (input)="downPct.set(+$any($event.target).value)"
                 min="3" max="50" step="1" />
        </div>
        <div class="calc-row">
          <label>Insurance ($/mo)</label>
          <div class="calc-input-wrap">
            <span>$</span>
            <input type="number"
                   [value]="insMonthly()"
                   (input)="insMonthly.set(+$any($event.target).value)"
                   min="0" max="1000" step="25" />
          </div>
        </div>
        <div class="calc-row">
          <label>Closing costs (%)</label>
          <input type="number"
                 [value]="closingCostPct()"
                 (input)="closingCostPct.set(+$any($event.target).value)"
                 min="0" max="10" step="0.5" />
        </div>
        @if (affordability(); as a) {
          <div class="calc-result">
            <div class="calc-max-price">\${{ a.maxPrice | number }}</div>
            <div class="calc-max-label">Max purchase price</div>
            <div class="calc-breakdown">
              <span>P&amp;I \${{ a.monthlyPI | number }}</span>
              <span>Tax \${{ a.monthlyTax | number }}</span>
              <span>Ins \${{ a.insMonthly | number }}</span>
            </div>
            <div class="calc-down">Down \${{ a.downAmount | number }} · Loan \${{ a.loanAmount | number }}</div>
            <div class="calc-closing">Est. closing costs \${{ a.closingCosts | number }} ({{ closingCostPct() }}%)</div>
          </div>
        }
        <div class="calc-note">30yr fixed · Dallas Co 1.85% tax (homestead est.)</div>
      </div>
    </div>
  `,
})
export class AffordabilityCalculatorComponent {
  maxMonthly      = signal(3500);
  mortgageRate    = signal(6.3);
  downPct         = signal(20);
  insMonthly      = signal(175);
  closingCostPct  = signal(3);

  affordability = computed(() => {
    const budget = this.maxMonthly();
    const rate   = this.mortgageRate();
    const down   = this.downPct();
    const ins    = this.insMonthly();
    const taxRate = 1.85;
    if (budget <= ins || rate <= 0 || down < 0 || down >= 100) return null;
    const r      = (rate / 100) / 12;
    const n      = 360;
    const factor = (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    const coeff  = (1 - down / 100) * factor + (taxRate / 100 / 12);
    const maxPrice = (budget - ins) / coeff;
    return {
      maxPrice:     Math.round(maxPrice),
      downAmount:   Math.round(maxPrice * down / 100),
      loanAmount:   Math.round(maxPrice * (1 - down / 100)),
      monthlyPI:    Math.round(maxPrice * (1 - down / 100) * factor),
      monthlyTax:   Math.round(maxPrice * taxRate / 100 / 12),
      insMonthly:   ins,
      closingCosts: Math.round(maxPrice * this.closingCostPct() / 100),
    };
  });
}

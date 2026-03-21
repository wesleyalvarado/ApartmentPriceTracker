import { ApplicationConfig } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { providePrimeNG } from 'primeng/config';
import Aura from '@primeng/themes/aura';
import { definePreset } from '@primeng/themes';
import { routes } from './app.routes';

const CamdenPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '#eaf2ed',
      100: '#c4dccb',
      200: '#9ec6a9',
      300: '#77b087',
      400: '#509965',
      500: '#2b5741',  // camden green
      600: '#244a37',
      700: '#1d3d2d',
      800: '#163023',
      900: '#0f2319',
      950: '#08160f',
    },
  },
});

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideAnimationsAsync(),
    provideHttpClient(),
    providePrimeNG({
      theme: {
        preset: CamdenPreset,
        options: { darkModeSelector: false },
      },
    }),
  ],
};

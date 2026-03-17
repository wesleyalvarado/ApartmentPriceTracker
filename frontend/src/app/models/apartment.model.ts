export interface Complex {
  id: number;
  name: string;
  display_name: string;
  city: string;
  state: string;
  url: string | null;
}

export interface FloorPlan {
  complex_id: number;
  complex_name: string;
  floorplan_name: string;
  floorplan_slug: string;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  available_units: number;
  min_price: number;
  max_price: number;
  avg_price: number;
  earliest_available: string | null;
  special_tags: string | null;
  scraped_at: string;
}

export interface Unit {
  complex_id: number;
  complex_name: string;
  floorplan_name: string;
  floorplan_slug: string;
  unit_id: string;
  floor: number | null;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  price: number;
  available_date: string | null;
  avail_note: string | null;
  special_tags: string | null;
  scraped_at: string;
  unit_features?: string | null;
}

export interface PricePoint {
  scraped_at: string;
  price?: number;
  min_price?: number;
  max_price?: number;
  avg_price?: number;
  unit_count?: number;
}

export interface Stats {
  complex_id: number;
  complex_name: string;
  floorplan_name: string;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  all_time_min: number;
  all_time_max: number;
  current_min: number;
  scrape_count: number;
  total_units_seen: number;
}

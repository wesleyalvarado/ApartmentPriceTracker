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
  image_url: string | null;
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

export interface RentedUnit {
  unit_id: string;
  floorplan_name: string;
  floor: number | null;
  bedrooms: number;
  last_price: number;
  last_available_date: string | null;
  last_seen: string;
}

export type StatusValue = 'available' | 'rented' | 'all';

export interface BedroomOption      { label: string; value: number | null; }
export interface LeaseTermOption    { label: string; value: number; }
export interface ComplexOption      { label: string; value: number | null; }
export interface AvailabilityOption { label: string; value: number | null; }
export interface StatusOption       { label: string; value: StatusValue; }

export interface DisplayUnit {
  unit_id: string;
  floor: number | null;
  price: number;
  available_date: string | null;
  status: 'available' | 'rented';
  last_seen?: string;
}

export interface DisplayFloorPlan extends FloorPlan {
  display_units: number;
  display_min: number;
  display_max: number;
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

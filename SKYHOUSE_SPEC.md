# SkyHouse Dallas (Victory Park) — Scraper Spec for Claude Code

> **Purpose**: Add SkyHouse Dallas as the second tracked complex in the existing Apartment Price Tracker. This document gives Claude Code everything it needs to build the scraper. The DB schema, API, and Angular frontend already support multi-complex — this is purely about getting the data in.

---

## Table of Contents

1. [Context: What Already Exists](#1-context-what-already-exists)
2. [Property Overview](#2-property-overview)
3. [Critical Technical Challenges](#3-critical-technical-challenges)
4. [Approach: Three Options (Try in Order)](#4-approach-three-options-try-in-order)
5. [Option A: RentCafe Public API (Best Case)](#5-option-a-rentcafe-public-api-best-case)
6. [Option B: Playwright Scraper (If API Fails)](#6-option-b-playwright-scraper-if-api-fails)
7. [Option C: Third-Party Listing Site Scrape (Fallback)](#7-option-c-third-party-listing-site-scrape-fallback)
8. [Lease-Term Pricing (4, 5, 6 Month)](#8-lease-term-pricing-4-5-6-month)
9. [Database Integration](#9-database-integration)
10. [File Structure](#10-file-structure)
11. [Exploration Steps (Run First)](#11-exploration-steps-run-first)
12. [Current Pricing Snapshot](#12-current-pricing-snapshot)

---

## 1. Context: What Already Exists

Refer to `PROGRESS.md` for full details. Key points:

- **Database**: SQLite at `data/camden_prices.db` with `complexes` table, `complex_id` FK on all data tables
- **Existing complex**: Camden Greenville (complex_id = 1)
- **Multi-complex support is fully wired**: API endpoints accept `?complex_id=N`, frontend shows a complex selector when 2+ exist
- **Lease term pricing**: `lease_term_prices` table exists, API supports `?lease_term=N`
- **Scraper pattern**: Site-specific scrapers live in `scraper/<complex_slug>/` directories

To add SkyHouse Dallas, we need to:
1. `INSERT INTO complexes` a new row (complex_id = 2)
2. Create `scraper/skyhouse_dallas/scraper.py` (and optionally `lease_terms.py`)
3. Run it — the frontend and API pick it up automatically

---

## 2. Property Overview

| Field | Value |
|-------|-------|
| **Name** | SkyHouse Dallas |
| **Display Name** | SkyHouse Dallas - Victory Park |
| **Address** | 2320 N Houston St, Dallas, TX 75219 |
| **Neighborhood** | Victory Park |
| **Management** | Simpson Property Group |
| **Tech Platform** | Yardi / RentCafe |
| **Total Units** | 336 |
| **Stories** | 24 |
| **Built** | 2015 |
| **Unit Types** | Studio, 1BR, 2BR, 3BR |
| **SqFt Range** | 573 – 1,403 sqft |
| **Price Range** | ~$1,540 – $3,910/mo |
| **Available Units** | ~27-50 (varies daily) |
| **Lease Terms** | 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14 months |
| **Website** | https://www.simpsonpropertygroup.com/apartments/dallas-texas/skyhouse-dallas-victory-park-downtown/apartment-floor-plans |
| **RentCafe Page** | https://www.rentcafe.com/apartments/tx/dallas/skyhouse-dallas/default.aspx |

### Known Floor Plan Model Names (from ApartmentHomeLiving)

| Model(s) | Beds | Baths | SqFt | Notes |
|----------|------|-------|------|-------|
| (studio models) | 0 | 1 | 573 | Starting ~$1,565 |
| D2, D3 | 1 | 1 | 681 | |
| F, FB, F1, F1B | 1 | 1 | 760 | Multiple variants |
| B2, B3 | 1 | 1 | ~700-760 | |
| (other 1BR) | 1 | 1 | 702, 723 | |
| (2BR models) | 2 | 2 | 991, 1016 | Starting ~$2,380 |
| G, H, J, K, L, L1 | 3 | 3 | 1,348-1,403 | Starting ~$2,785 |

---

## 3. Critical Technical Challenges

### 3A. The Website Blocks Direct HTTP Requests

**simpsonpropertygroup.com returns HTTP 403** on all direct fetches — confirmed via multiple attempts with both `requests` and fetch tools. This is a bot protection layer (likely Cloudflare, Akamai, or similar WAF).

This means:
- ❌ `requests` + BeautifulSoup will NOT work (unlike Camden)
- ❌ `curl` will NOT work
- ✅ Playwright/Selenium with a real browser engine CAN work (renders JS, handles challenges)
- ✅ RentCafe API may bypass this entirely (structured data, no scraping)

### 3B. Different Tech Stack from Camden

| | Camden Greenville | SkyHouse Dallas |
|--|-------------------|-----------------|
| **Framework** | Next.js (SSR) | Unknown (Yardi/RentCafe-powered) |
| **Data Source** | `__NEXT_DATA__` JSON + GraphQL API | RentCafe API (probable) or JS-rendered HTML |
| **Bot Protection** | None (requests work fine) | 403 on direct HTTP |
| **Lease Pricing** | Camden GraphQL API (public, no auth) | Unknown — likely RentCafe API or JS widget |
| **Scraping Approach** | Pure HTTP + JSON parsing | Playwright required, OR RentCafe API |

### 3C. This Needs a Completely Separate Scraper

As noted in PROGRESS.md: "Different platforms need completely different parsing logic — there is no shared parsing code." The SkyHouse scraper will share only the DB schema and `COMPLEX_ID` convention with the Camden scraper.

---

## 4. Approach: Three Options (Try in Order)

Try these in sequence. Stop as soon as one works.

```
Option A: RentCafe API  ← Try this first (cleanest, fastest, most reliable)
    ↓ (if propertyId not found or API blocked)
Option B: Playwright     ← Scrape the actual Simpson website with headless browser
    ↓ (if bot detection defeats Playwright)
Option C: Third-party    ← Scrape from ApartmentList, Apartments.com, or Zillow
```

---

## 5. Option A: RentCafe Public API (Best Case)

### Background

Yardi's RentCafe platform exposes a public REST API at:
```
https://api.rentcafe.com/rentcafeapi.aspx
```

This API returns JSON with full unit-level availability, pricing, floor plans, and more. **No authentication required** — just needs the property's `propertyId`.

### The Missing Piece: Finding the `propertyId`

The propertyId is a numeric ID that Yardi assigns to each property. It's typically embedded in:
- The RentCafe page source (`rentcafe.com/apartments/tx/dallas/skyhouse-dallas/`)
- The Simpson Property Group page source (in a JS config object or data attribute)
- XHR requests visible in the browser's Network tab when loading the floor plans page

### Exploration Steps (DO THIS FIRST)

```python
# Step 1: Use Playwright to load the Simpson site and extract the propertyId
# from page source, XHR calls, or embedded config.

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headful to see what happens
    page = browser.new_page()

    # Navigate to the floor plans page
    page.goto("https://www.simpsonpropertygroup.com/apartments/dallas-texas/skyhouse-dallas-victory-park-downtown/apartment-floor-plans")

    # Wait for content to load
    page.wait_for_load_state("networkidle")

    # Look for propertyId in page source
    content = page.content()
    # Search for patterns like: propertyId, PropertyId, property_id, rentcafe
    import re
    ids = re.findall(r'(?:propertyId|PropertyId|property_id)["\s:=]+(\d+)', content)
    print(f"Found property IDs: {ids}")

    # Also check for RentCafe API calls in the network traffic
    # The page may make XHR calls to api.rentcafe.com

    # Check all script tags for config objects
    scripts = page.query_selector_all("script")
    for s in scripts:
        text = s.text_content()
        if text and ("rentcafe" in text.lower() or "propertyid" in text.lower() or "yardi" in text.lower()):
            print(f"Found relevant script: {text[:500]}")

    input("Press Enter to close browser...")  # Keep open for manual inspection
    browser.close()
```

```python
# Step 2: Also try to intercept XHR traffic for API calls

from playwright.sync_api import sync_playwright

def log_request(request):
    if "rentcafe" in request.url.lower() or "api" in request.url.lower():
        print(f"API CALL: {request.method} {request.url}")

def log_response(response):
    if "rentcafe" in response.url.lower() or "api" in response.url.lower():
        print(f"API RESPONSE: {response.status} {response.url}")
        try:
            print(f"  Body preview: {response.text()[:500]}")
        except:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.on("request", log_request)
    page.on("response", log_response)

    page.goto("https://www.simpsonpropertygroup.com/apartments/dallas-texas/skyhouse-dallas-victory-park-downtown/apartment-floor-plans")
    page.wait_for_load_state("networkidle")

    # Click around to trigger pricing loads
    # Look for "Available Apartments" section, floor plan cards, etc.

    input("Press Enter to close...")
    browser.close()
```

### Once You Have the `propertyId`

If you find it (let's say it's `12345` as a placeholder), the RentCafe API calls are:

```python
import requests

PROPERTY_ID = "XXXXX"  # ← Replace with the actual ID found above
BASE = "https://api.rentcafe.com/rentcafeapi.aspx"

# Get all available apartments
response = requests.get(BASE, params={
    "requestType": "apartmentavailability",
    "propertyId": PROPERTY_ID,
    "showallunit": "-1",  # Include occupied/unavailable units too
})
data = response.json()

# Each item in the response typically includes:
# - ApartmentId (unique unit ID)
# - ApartmentName (unit number like "607")
# - FloorplanName (like "D2")
# - Beds, Baths, SQFT
# - MinimumRent, MaximumRent (or just Rent)
# - AvailableDate
# - FloorNumber
# - Amenities, Features
# - IsAvailable

# Get floor plan info
response = requests.get(BASE, params={
    "requestType": "floorplan",
    "propertyId": PROPERTY_ID,
})
floorplans = response.json()

# Get property info
response = requests.get(BASE, params={
    "requestType": "property",
    "propertyId": PROPERTY_ID,
})
property_info = response.json()
```

### RentCafe API Response Structure (Typical)

```json
[
  {
    "PropertyId": "12345",
    "FloorplanId": "67",
    "FloorplanName": "D2",
    "ApartmentId": "98765",
    "ApartmentName": "607",
    "Beds": "1",
    "Baths": "1",
    "SQFT": "681",
    "MinimumRent": "1975.00",
    "MaximumRent": "1975.00",
    "AvailableDate": "02/17/2026",
    "IsAvailable": "True",
    "FloorNumber": "6",
    "UnitImageURL": "...",
    "Amenities": "Balcony, Dishwasher, Washer/Dryer In Unit"
  },
  ...
]
```

### If the API Works, the Scraper is Simple

```python
# scraper/skyhouse_dallas/scraper.py

import requests
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

PROPERTY_ID = "XXXXX"  # Found via exploration
COMPLEX_ID = 2
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "camden_prices.db"
API_BASE = "https://api.rentcafe.com/rentcafeapi.aspx"

def fetch_availability():
    resp = requests.get(API_BASE, params={
        "requestType": "apartmentavailability",
        "propertyId": PROPERTY_ID,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()

def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    units = fetch_availability()
    available = [u for u in units if u.get("IsAvailable") == "True"]

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    for u in available:
        conn.execute("""
            INSERT INTO price_snapshots
                (scraped_at, complex_id, floorplan_name, unit_id, floor,
                 bedrooms, bathrooms, sqft, price, available_date,
                 avail_note, special_tags, unit_features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            COMPLEX_ID,
            u.get("FloorplanName", "Unknown"),
            u.get("ApartmentName", u.get("ApartmentId", "")),
            int(u["FloorNumber"]) if u.get("FloorNumber") else None,
            float(u.get("Beds", 0)),
            float(u.get("Baths", 1)),
            int(float(u.get("SQFT", 0))),
            int(float(u.get("MinimumRent", 0))),
            _parse_date(u.get("AvailableDate")),
            None,
            None,
            json.dumps(u.get("Amenities", "").split(", ")) if u.get("Amenities") else None,
        ))

    conn.commit()
    conn.close()
    print(f"Inserted {len(available)} units for SkyHouse Dallas at {now}")

def _parse_date(date_str):
    if not date_str:
        return None
    try:
        parts = date_str.split("/")
        return f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
    except:
        return date_str

if __name__ == "__main__":
    main()
```

---

## 6. Option B: Playwright Scraper (If API Fails)

If the RentCafe API approach doesn't pan out (no propertyId found, or API is gated), use Playwright to load the Simpson website directly.

### Dependencies

```
# Add to scraper/requirements.txt
playwright>=1.42.0
```

```bash
# Install browser engines
playwright install chromium
```

### Approach

```python
# scraper/skyhouse_dallas/scraper.py (Playwright version)

from playwright.sync_api import sync_playwright
import sqlite3
import re
import json
import time
import random
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.simpsonpropertygroup.com/apartments/dallas-texas/skyhouse-dallas-victory-park-downtown/apartment-floor-plans"
COMPLEX_ID = 2
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "camden_prices.db"

def scrape():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.goto(URL, wait_until="networkidle")

        # Wait for the available apartments section to load
        # The page likely has floor plan cards or a unit table
        # that renders after JS execution
        page.wait_for_timeout(3000)

        # Strategy 1: Check for __NEXT_DATA__ (unlikely but possible)
        next_data = page.query_selector("script#__NEXT_DATA__")
        if next_data:
            data = json.loads(next_data.text_content())
            # Parse Next.js data structure
            pass

        # Strategy 2: Check for embedded JSON/config in any script tags
        scripts = page.query_selector_all("script")
        for s in scripts:
            text = s.text_content() or ""
            if "floorplan" in text.lower() or "apartment" in text.lower():
                # Try to extract JSON data
                pass

        # Strategy 3: Parse the rendered DOM
        # Look for floor plan cards, unit lists, prices
        content = page.content()

        # The page likely shows cards similar to:
        # - Floor plan name/image
        # - Beds/baths/sqft
        # - "Starting at $X,XXX"
        # - "Available MM/DD/YYYY"
        # - Individual unit numbers

        # Save raw HTML for analysis
        snapshot_dir = DB_PATH.parent / "snapshots" / "skyhouse_dallas"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        safe_ts = now.replace(":", "-")
        (snapshot_dir / f"floorplans_{safe_ts}.html").write_text(content)

        # PARSE THE PAGE — exact selectors TBD after inspection
        # This is where you'll need to adapt based on the actual DOM structure
        #
        # Common patterns on RentCafe-powered sites:
        # - .fp-card or .floorplan-card containers
        # - .unit-row or .availability-row for individual units
        # - data-* attributes with unit IDs and prices
        # - A "View Available" button that expands unit lists
        #
        # If the page has a "scroll to load" or "click to expand" pattern,
        # you may need to click elements to reveal all units.

        units = parse_rendered_page(page)

        browser.close()

    # Insert into database
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    for u in units:
        conn.execute("""
            INSERT INTO price_snapshots
                (scraped_at, complex_id, floorplan_name, unit_id, floor,
                 bedrooms, bathrooms, sqft, price, available_date,
                 avail_note, special_tags, unit_features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (now, COMPLEX_ID, u["floorplan"], u["unit_id"], u.get("floor"),
              u["beds"], u["baths"], u["sqft"], u["price"],
              u.get("available_date"), None, None, None))
    conn.commit()
    conn.close()
    print(f"Inserted {len(units)} units at {now}")


def parse_rendered_page(page):
    """
    Parse the rendered DOM for apartment data.
    ADAPT THIS based on actual page structure discovered during exploration.
    """
    units = []
    # TODO: Implement after inspecting the actual rendered DOM
    # Key: the page structure is UNKNOWN until you load it in a browser
    # and inspect with DevTools. The exploration script (Section 11) helps.
    return units


if __name__ == "__main__":
    scrape()
```

---

## 7. Option C: Third-Party Listing Site Scrape (Fallback)

If both the RentCafe API and direct Playwright scraping fail, scrape from a listing aggregator that has the data:

| Source | URL | Pros | Cons |
|--------|-----|------|------|
| ApartmentList | apartmentlist.com/tx/dallas/skyhouse-dallas-apartments | Has per-unit pricing, updates frequently | May also block scraping |
| Apartments.com | apartments.com/skyhouse-dallas-apartments-dallas-tx/ypzcl6r/ | Most comprehensive data | Heavy bot protection |
| Zillow | zillow.com/apartments/dallas-tx/skyhouse-dallas-apartments/5gq6x6/ | Has interactive unit map | API-based, harder to scrape |
| RentCafe | rentcafe.com/apartments/tx/dallas/skyhouse-dallas/ | Source of truth (Yardi data) | Also 403'd in testing |

This is the least preferred option because:
- Third-party data may lag behind the source
- These sites all have bot protection
- Prices may not match the property's actual current pricing
- Lease-term pricing is unlikely to be available

---

## 8. Lease-Term Pricing (4, 5, 6 Month)

### What We Know

ApartmentList confirms: **"We offer 4-14 month lease terms. Lease terms vary based on floor plan and availability. Please note leases shorter than 12 months often have extra fees."**

### How to Get It

This depends on which Option (A/B/C) works for base pricing:

**If Option A (RentCafe API) works:**
The RentCafe API may support a `leaseTerm` parameter:
```python
response = requests.get(API_BASE, params={
    "requestType": "apartmentavailability",
    "propertyId": PROPERTY_ID,
    "leaseTerm": 4,  # or 5, 6
})
```
Test this — if it returns different prices per lease term, you're done.

**If Option B (Playwright) works:**
The floor plans page likely has a lease-term selector (dropdown or radio buttons) similar to Camden's "Your Custom Quote" section. Use Playwright to:
1. Load the page
2. Select each lease term (4, 5, 6 months)
3. Capture the updated prices
4. This may trigger XHR calls you can intercept (like Camden's GraphQL)

**Key insight from Camden**: Camden had a hidden GraphQL API that returned lease-term pricing. SkyHouse/Yardi may have a similar hidden API. The Playwright network interception script in Section 5 will capture any API calls made when switching lease terms.

### Lease Term Scraper Structure

```python
# scraper/skyhouse_dallas/lease_terms.py

# Pattern matching Camden's lease_terms.py:
# 1. For each available unit
# 2. For each lease term [4, 5, 6]
# 3. Query the pricing API (RentCafe or discovered endpoint)
# 4. Insert into lease_term_prices table

LEASE_TERMS = [4, 5, 6]  # User requested these specifically
```

---

## 9. Database Integration

### Step 1: Insert the Complex

```sql
INSERT INTO complexes (name, display_name, city, state, url, community_id)
VALUES (
    'skyhouse_dallas',
    'SkyHouse Dallas - Victory Park',
    'Dallas',
    'TX',
    'https://www.simpsonpropertygroup.com/apartments/dallas-texas/skyhouse-dallas-victory-park-downtown/apartment-floor-plans',
    NULL  -- Set community_id if RentCafe propertyId is found
);
-- This will auto-assign complex_id = 2 (assuming Camden is 1)
```

### Step 2: Verify COMPLEX_ID

```python
# In the scraper, verify:
cursor = conn.execute("SELECT id FROM complexes WHERE name = 'skyhouse_dallas'")
row = cursor.fetchone()
COMPLEX_ID = row[0]  # Should be 2
```

### Floorplan Meta

After the first successful scrape, also populate `floorplan_meta`:

```python
# Insert/update floorplan metadata
conn.execute("""
    INSERT OR REPLACE INTO floorplan_meta
        (complex_id, floorplan_name, floorplan_slug, floor, bedrooms, bathrooms, sqft, special_tags, last_updated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (COMPLEX_ID, floorplan_name, slug, None, beds, baths, sqft, None, now))
```

---

## 10. File Structure

```
scraper/
├── camden_greenville/          # existing
│   ├── scraper.py
│   ├── lease_terms.py
│   ├── parser.py
│   └── ...
├── skyhouse_dallas/            # NEW
│   ├── scraper.py              # Main scraper (Option A, B, or C)
│   ├── lease_terms.py          # Lease-term pricing (4, 5, 6 month)
│   ├── explore.py              # Exploration script to find APIs/IDs
│   └── README.md               # Notes on what worked, what didn't
├── migrate_add_complexes.py    # existing (already run)
└── requirements.txt            # add playwright if needed
```

---

## 11. Exploration Steps (Run First)

**Before writing the actual scraper, run these discovery steps.** The results determine which Option (A/B/C) to implement.

### Step 1: Load the Page in Playwright (Headful) and Inspect

```python
#!/usr/bin/env python3
"""
explore.py — Discovery script for SkyHouse Dallas.
Run headful (not headless) so you can see and interact with the page.
Check the terminal output for API calls, property IDs, etc.
"""

import re
import json
from playwright.sync_api import sync_playwright

URLS = [
    "https://www.simpsonpropertygroup.com/apartments/dallas-texas/skyhouse-dallas-victory-park-downtown/apartment-floor-plans",
]

api_calls = []

def on_request(request):
    url = request.url.lower()
    if any(kw in url for kw in ["rentcafe", "api", "graphql", "availability", "floorplan", "pricing", "yardi"]):
        api_calls.append({"method": request.method, "url": request.url, "headers": dict(request.headers)})
        print(f"\n🔵 API REQUEST: {request.method} {request.url}")
        if request.post_data:
            print(f"   POST body: {request.post_data[:500]}")

def on_response(response):
    url = response.url.lower()
    if any(kw in url for kw in ["rentcafe", "api", "graphql", "availability", "floorplan", "pricing", "yardi"]):
        print(f"🟢 API RESPONSE: {response.status} {response.url}")
        try:
            body = response.text()
            print(f"   Body preview: {body[:800]}")
        except:
            pass

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.on("request", on_request)
        page.on("response", on_response)

        for url in URLS:
            print(f"\n{'='*60}")
            print(f"Loading: {url}")
            print(f"{'='*60}")
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(5000)

        # Dump full page source for analysis
        content = page.content()
        with open("skyhouse_page_source.html", "w") as f:
            f.write(content)
        print(f"\nSaved page source ({len(content):,} chars) to skyhouse_page_source.html")

        # Search for property IDs in page source
        print("\n--- Searching page source for IDs ---")
        for pattern in [
            r'(?:propertyId|PropertyId|property_id|propId)["\s:=]+["\']?(\d+)',
            r'rentcafe[^"]*?(\d{4,})',
            r'(?:communityId|community_id)["\s:=]+["\']?(\d+)',
            r'(?:yardiId|yardi_id)["\s:=]+["\']?(\d+)',
        ]:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                print(f"  Pattern '{pattern[:40]}...' → {matches[:5]}")

        # Search for RentCafe or Yardi references
        print("\n--- Script tags mentioning rentcafe/yardi/api ---")
        scripts = page.query_selector_all("script")
        for i, s in enumerate(scripts):
            text = s.text_content() or ""
            if any(kw in text.lower() for kw in ["rentcafe", "yardi", "propertyid", "floorplan", "availability"]):
                print(f"\n  Script #{i} ({len(text)} chars):")
                print(f"  {text[:400]}...")

        print(f"\n\nTotal API calls intercepted: {len(api_calls)}")
        for call in api_calls:
            print(f"  {call['method']} {call['url']}")

        input("\n\nPress Enter to close browser (inspect DevTools first!)...")
        browser.close()

if __name__ == "__main__":
    main()
```

### Step 2: Try the RentCafe API with Discovered Property ID

```python
#!/usr/bin/env python3
"""Test RentCafe API once you have a candidate propertyId."""

import requests
import json
import sys

PROPERTY_ID = sys.argv[1] if len(sys.argv) > 1 else "XXXXX"
BASE = "https://api.rentcafe.com/rentcafeapi.aspx"

print(f"Testing RentCafe API with propertyId={PROPERTY_ID}")

# Test 1: Property info
print("\n--- Property Info ---")
try:
    r = requests.get(BASE, params={"requestType": "property", "propertyId": PROPERTY_ID}, timeout=10)
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json()[:1] if isinstance(r.json(), list) else r.json(), indent=2)[:500])
except Exception as e:
    print(f"Error: {e}")

# Test 2: Floor plans
print("\n--- Floor Plans ---")
try:
    r = requests.get(BASE, params={"requestType": "floorplan", "propertyId": PROPERTY_ID}, timeout=10)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Found {len(data)} floor plans")
    if data:
        print(json.dumps(data[0], indent=2)[:500])
except Exception as e:
    print(f"Error: {e}")

# Test 3: Available apartments
print("\n--- Available Apartments ---")
try:
    r = requests.get(BASE, params={"requestType": "apartmentavailability", "propertyId": PROPERTY_ID}, timeout=10)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Found {len(data)} apartments")
    if data:
        print(json.dumps(data[0], indent=2)[:500])
except Exception as e:
    print(f"Error: {e}")

# Test 4: With lease term
for term in [4, 5, 6, 14]:
    print(f"\n--- Lease Term = {term} months ---")
    try:
        r = requests.get(BASE, params={
            "requestType": "apartmentavailability",
            "propertyId": PROPERTY_ID,
            "leaseTerm": term,
        }, timeout=10)
        data = r.json()
        if data and isinstance(data, list):
            sample = data[0]
            print(f"  Unit {sample.get('ApartmentName')}: ${sample.get('MinimumRent')}/mo")
    except Exception as e:
        print(f"  Error: {e}")
```

### Step 3: Document What You Find

After running the exploration scripts, update `scraper/skyhouse_dallas/README.md` with:
- Which Option (A/B/C) worked
- The propertyId (if found)
- The exact API endpoint and parameters
- Any API response quirks
- The DOM structure (if scraping HTML)

---

## 12. Current Pricing Snapshot (March 17, 2026)

From third-party sources — use this to validate your scraper output:

| Source | Available Units | Price Range | Last Updated |
|--------|----------------|-------------|--------------|
| ApartmentList | 29 | $1,570 – $3,145 | 3 hours ago |
| Apartments.com | N/A | $1,710 – $3,910 | 2 days ago |
| RentCafe | N/A | from $1,540 | Today |
| ApartmentHomeLiving | ~27+ | $1,570 – $3,005 | Jan 27, 2026 |
| ApartmentList (newer) | 50 | from $1,715 | Recent |

Floor plan types confirmed across sources:
- **Studio**: ~573 sqft, from ~$1,540-1,710
- **1BR/1BA**: 681-760 sqft, from ~$1,870-1,975
- **2BR/2BA**: 991-1,016 sqft, from ~$2,380
- **3BR/3BA**: 1,348-1,403 sqft, from ~$2,785

---

## Build Order

1. **Run `explore.py`** — Discover the propertyId, API endpoints, page structure
2. **Try RentCafe API** — If propertyId found, test with `test_rentcafe.py`
3. **Build the scraper** — Based on whichever option works
4. **Insert the complex** — `INSERT INTO complexes ...`
5. **First run** — Execute scraper, verify data in SQLite
6. **Build lease_terms.py** — Adapt based on discovered API/endpoint for lease pricing
7. **Verify frontend** — The complex selector should appear automatically
8. **Add to schedule** — Alongside Camden scraper in cron/launchd

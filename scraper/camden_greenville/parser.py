"""parser.py — HTML parsing logic for Camden Greenville apartments.

The Camden website is built with Next.js and embeds ALL data inside a
<script id="__NEXT_DATA__"> tag as JSON. We parse that JSON directly
rather than scraping the visible HTML, which is far more reliable.

Main page __NEXT_DATA__ structure:
  props.pageProps.data.availableApartments[]
    .name, .slug, .bedrooms, .bathrooms, .squareFeet
    .monthlyRent        ← cheapest unit's price
    .availableUnitIds[] ← ALL unit IDs for this floor plan
    .unitName           ← cheapest unit's ID
    .moveInDate

Detail page __NEXT_DATA__ structure (loaded with ?unit=XXXX):
  props.pageProps.data.floorPlan
    .name, .slug, .squareFeet, .bedrooms, .bathrooms
    .units[0]
      .unitName, .monthlyRent, .moveInDate, .floorNumber
      .features[].feature
"""

import re
import json
from datetime import date, timedelta
from bs4 import BeautifulSoup


# ── Public parsing functions ──────────────────────────────────────────────────

def parse_main_page(html: str) -> list[dict]:
    """
    Parse the main listing page via __NEXT_DATA__ JSON.

    Returns one dict per floor plan:
        name, slug, floor, beds, baths, sqft,
        starting_price, available_date, avail_note,
        special_tags, detail_url, default_unit_id,
        available_unit_ids   ← NEW: full list of all available unit IDs
    """
    next_data = _extract_next_data(html)
    if not next_data:
        return []

    try:
        avail_apts = next_data["props"]["pageProps"]["data"]["availableApartments"]
    except (KeyError, TypeError):
        return []

    # Also parse special_tags from HTML (not in JSON)
    tag_map = _parse_all_tags_from_html(html)

    # Also grab the floor parameter per floor plan from the See More links
    floor_map = _parse_floor_from_see_more_links(html)

    results = []
    for ap in avail_apts:
        name = ap.get("name", "")
        if not name:
            continue

        slug = name.lower().replace(" ", "-") + "-floor-plan"
        beds = _normalize_bedrooms(ap.get("bedrooms", "0"))
        baths = float(ap.get("bathrooms") or 1)
        sqft = int(ap.get("squareFeet") or 0)
        price = int(ap.get("monthlyRent") or 0)
        unit_ids = ap.get("availableUnitIds") or []
        default_unit = ap.get("unitName") or ap.get("unitNumber")
        move_in = ap.get("moveInDate", "")
        available_date = move_in[:10] if move_in else None  # "2026-03-18T00:00:00.000Z" → "2026-03-18"
        avail_count = int(ap.get("availableUnits") or len(unit_ids))

        media = ap.get("media") or {}
        image_url = media.get("floorPlanImage")

        results.append({
            "name": name,
            "slug": slug,
            "floor": floor_map.get(slug),        # from See More href ?floor=N
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "starting_price": price,
            "available_date": available_date,
            "avail_note": build_avail_note(avail_count),
            "special_tags": tag_map.get(name),   # from HTML buttons
            "detail_url": None,
            "default_unit_id": default_unit,
            "available_unit_ids": unit_ids,
            "image_url": image_url,
        })

    return results


def parse_unit_list(html: str) -> list[str]:
    """
    Extract all available unit IDs from a floor plan detail page.

    Reads from __NEXT_DATA__ JSON first; falls back to HTML parsing.
    Returns list of unit ID strings, e.g. ["3304", "6303", "2305"].
    """
    next_data = _extract_next_data(html)
    if next_data:
        try:
            fp = next_data["props"]["pageProps"]["data"]["floorPlan"]
            # 'units' on the detail page only has the selected unit,
            # but the availableApartments or availableUnit key may have all IDs.
            # Check for availableUnit key
            avail_unit = next_data["props"]["pageProps"]["data"].get("availableUnit")
            if avail_unit:
                ids = avail_unit.get("availableUnitIds") or []
                if ids:
                    return [str(uid) for uid in ids]
        except (KeyError, TypeError):
            pass

    # HTML fallback: look for the Available ... Apartments (N) heading
    return _parse_unit_list_from_html(html)


def parse_all_units_from_detail(html: str, floorplan_info: dict) -> list[dict]:
    """
    Parse ALL available units from a floor plan detail page.

    The detail page __NEXT_DATA__ contains floorPlan.units[] with one entry
    per available unit, each with its own price, availability date, and floor number.

    Returns list of unit dicts ready for insertion into price_snapshots.
    Returns empty list if parsing fails (caller should fall back to main-page data).
    """
    next_data = _extract_next_data(html)
    if not next_data:
        return []

    try:
        units = next_data["props"]["pageProps"]["data"]["floorPlan"]["units"]
    except (KeyError, TypeError):
        return []

    results = []
    for unit in units:
        unit_id = str(unit.get("unitName") or unit.get("unitId") or "")
        price = int(unit.get("monthlyRent") or 0)
        if not unit_id or not price:
            continue

        move_in = unit.get("moveInDate", "")
        available_date = move_in[:10] if move_in else None

        floor = unit.get("floorNumber")
        floor = int(floor) if floor else floorplan_info.get("floor")

        features = [
            f["feature"]
            for f in (unit.get("features") or [])
            if f.get("feature")
        ]

        results.append({
            "floorplan_name": floorplan_info["name"],
            "floorplan_slug": floorplan_info["slug"],
            "unit_id": unit_id,
            "floor": floor,
            "bedrooms": floorplan_info["beds"],
            "bathrooms": floorplan_info["baths"],
            "sqft": floorplan_info["sqft"],
            "price": price,
            "available_date": available_date,
            "avail_note": None,  # set by caller
            "special_tags": floorplan_info.get("special_tags"),
            "unit_features": json.dumps(features) if features else None,
        })

    return results


def parse_unit_detail(html: str, floorplan_info: dict) -> dict:
    """
    Parse a unit-specific detail page loaded with ?unit={ID}&floor={N}.

    Reads from __NEXT_DATA__ JSON for price, features, floor number.
    Falls back to HTML parsing for price if JSON extraction fails.

    Args:
        html:            page HTML
        floorplan_info:  dict from parse_main_page (beds, baths, sqft, etc.)

    Returns dict with unit-specific price, features, and floor plan metadata.
    """
    next_data = _extract_next_data(html)
    unit_data = _extract_unit_from_next_data(next_data)

    # Determine unit_id
    unit_id = None
    if unit_data:
        unit_id = str(unit_data.get("unitName") or unit_data.get("unitId") or "")
    if not unit_id:
        unit_id = _extract_unit_id_from_html(html)

    # Price
    price = 0
    if unit_data:
        price = int(unit_data.get("monthlyRent") or 0)
    if not price:
        price = _parse_price_from_html(html)

    # Available date
    available_date = None
    if unit_data:
        move_in = unit_data.get("moveInDate", "")
        available_date = move_in[:10] if move_in else None
    if not available_date:
        available_date = _parse_date_from_html(html)

    # Floor number (from JSON is the actual unit floor, not the URL param)
    floor = floorplan_info.get("floor")
    if unit_data and unit_data.get("floorNumber"):
        floor = int(unit_data["floorNumber"])

    # Features
    features = []
    if unit_data:
        features = [
            f["feature"]
            for f in (unit_data.get("features") or [])
            if f.get("feature")
        ]

    return {
        "floorplan_name": floorplan_info["name"],
        "floorplan_slug": floorplan_info["slug"],
        "unit_id": unit_id or None,
        "floor": floor,
        "bedrooms": floorplan_info["beds"],
        "bathrooms": floorplan_info["baths"],
        "sqft": floorplan_info["sqft"],
        "price": price,
        "available_date": available_date,
        "avail_note": floorplan_info.get("avail_note"),
        "special_tags": floorplan_info.get("special_tags"),
        "unit_features": json.dumps(features) if features else None,
    }


# ── Private: JSON extraction ──────────────────────────────────────────────────

def _extract_next_data(html: str) -> dict | None:
    """Extract and parse the __NEXT_DATA__ JSON payload embedded in the page."""
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        return json.loads(tag.string)
    except (json.JSONDecodeError, ValueError):
        return None


def _extract_unit_from_next_data(next_data: dict | None) -> dict | None:
    """
    Extract the unit dict from the detail page's floorPlan.units[0].
    Returns None if not found.
    """
    if not next_data:
        return None
    try:
        units = next_data["props"]["pageProps"]["data"]["floorPlan"]["units"]
        return units[0] if units else None
    except (KeyError, TypeError, IndexError):
        return None


def _parse_floor_from_see_more_links(html: str) -> dict[str, int]:
    """
    Extract ?floor=N from the 'See More' links on the main page.
    Returns {slug: floor_number} mapping.
    """
    result: dict[str, int] = {}
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", attrs={"data-price": True}):
        href = a.get("href", "")
        slug_m = re.search(r"available-apartments/([^?]+)", href)
        floor_m = re.search(r"floor=(\d+)", href)
        if slug_m and floor_m:
            result[slug_m.group(1)] = int(floor_m.group(1))
    return result


def _parse_all_tags_from_html(html: str) -> dict[str, str | None]:
    """
    Extract special tags (Flex Space, Private Garage) per floor plan from HTML.
    Returns {floor_plan_name: tags_string}.
    """
    result: dict[str, str | None] = {}
    soup = BeautifulSoup(html, "lxml")

    # Each See More button has data-floor-plan-name attr
    for a in soup.find_all("a", attrs={"data-floor-plan-name": True}):
        name = a.get("data-floor-plan-name", "")
        if not name:
            continue
        # Walk up to the card container and look for tag text
        card = a
        for _ in range(8):
            if card.parent is None:
                break
            card = card.parent
            card_text = card.get_text()
            if "Starting Price" in card_text:
                tags = []
                if "Flex Space" in card_text:
                    tags.append("Flex Space")
                if "Private Garage" in card_text:
                    tags.append("Private Garage")
                result[name] = ", ".join(tags) if tags else None
                break
    return result


# ── Private: HTML fallbacks ───────────────────────────────────────────────────

def _parse_unit_list_from_html(html: str) -> list[str]:
    """Fallback: extract unit IDs from visible HTML."""
    soup = BeautifulSoup(html, "lxml")
    unit_ids: list[str] = []

    avail_heading = soup.find(
        string=re.compile(r"Available\s+.+\s+Apartments?\s*\(\d+\)", re.IGNORECASE)
    )
    if avail_heading:
        container = avail_heading.parent
        for _ in range(6):
            if not (container and container.parent):
                break
            container = container.parent
            items = container.find_all("li")
            for li in items:
                text = li.get_text(strip=True)
                if re.match(r"^\d{3,5}$", text):
                    unit_ids.append(text)
            if unit_ids:
                break

    if not unit_ids:
        seen: set[str] = set()
        for el in soup.find_all(string=re.compile(r"^\d{3,5}$")):
            text = el.strip()
            if text and text not in seen:
                unit_ids.append(text)
                seen.add(text)

    return unit_ids


def _extract_unit_id_from_html(html: str) -> str | None:
    """Extract unit ID from page title or URL in HTML."""
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    if title_tag:
        m = re.match(r"^(\d{3,5})[,\s]", title_tag.get_text(strip=True))
        if m:
            return m.group(1)
    m = re.search(r"unit=(\d{3,5})", str(soup))
    return m.group(1) if m else None


def _parse_price_from_html(html: str) -> int:
    """Fallback price extraction from raw HTML text (handles split elements)."""
    # Use raw HTML string with regex — avoids the BS4 separator splitting $ from digits
    m = re.search(
        r"Starting Price[^$<]{0,30}\$[^0-9]{0,5}([\d,]+)",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return int(m.group(1).replace(",", ""))
    # Any rent-range dollar amount
    for m in re.finditer(r"\$([\d,]+)", html):
        val = int(m.group(1).replace(",", ""))
        if 500 <= val <= 20_000:
            return val
    return 0


def _parse_date_from_html(html: str) -> str | None:
    """Fallback date extraction from HTML text."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text()
    if re.search(r"\bTomorrow\b", text, re.IGNORECASE):
        return (date.today() + timedelta(days=1)).isoformat()
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
    if m:
        parts = m.group(1).split("/")
        return f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
    return None


# ── Private: field normalization ──────────────────────────────────────────────

def _normalize_bedrooms(raw) -> float:
    if str(raw).lower() in ("studio", "0", ""):
        return 0.0
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def build_avail_note(unit_count: int) -> str:
    if unit_count <= 0:
        return "Available"
    if unit_count == 1:
        return "Last 1 Available!"
    if unit_count <= 3:
        return f"Only {unit_count} Available!"
    return "Available"


# ── Kept for backwards compatibility and unit tests ───────────────────────────

def _parse_bedrooms(text: str) -> float:
    if re.search(r"\bStudio\b", text, re.IGNORECASE):
        return 0.0
    m = re.search(r"(\d+)\s*Beds?", text, re.IGNORECASE)
    return float(m.group(1)) if m else 0.0


def _parse_bathrooms(text: str) -> float:
    m = re.search(r"([\d.]+)\s*Baths?", text, re.IGNORECASE)
    return float(m.group(1)) if m else 1.0


def _parse_sqft(text: str) -> int:
    m = re.search(r"([\d,]+)\s*SqFt", text, re.IGNORECASE)
    return int(m.group(1).replace(",", "")) if m else 0


def _parse_price(text: str) -> int:
    m = re.search(r"Starting Price[^$]*\$([\d,]+)", text, re.DOTALL | re.IGNORECASE)
    if m:
        return int(m.group(1).replace(",", ""))
    for m in re.finditer(r"\$([\d,]+)", text):
        val = int(m.group(1).replace(",", ""))
        if 500 <= val <= 20_000:
            return val
    return 0

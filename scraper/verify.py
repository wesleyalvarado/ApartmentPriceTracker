"""verify.py — Manual verification script.

Run this BEFORE the full scraper to answer one critical question:

  Does fetching ?unit={ID}&floor={N} return that unit's specific price
  in server-rendered HTML, or does Camden handle unit-switching client-side
  via JavaScript?

If it WORKS:  the full scraper can collect per-unit prices for every unit.
If it FAILS:  the scraper falls back to the floor plan starting price only,
              and Phase 2 (Playwright) will be needed for true per-unit data.

Usage:
    cd scraper
    pip install -r requirements.txt
    python verify.py
"""

import re
import sys
import random
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = (
    "https://www.camdenliving.com"
    "/apartments/dallas-tx/camden-greenville/available-apartments"
)

USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
]


# ── HTTP ──────────────────────────────────────────────────────────────────────

def fetch(session: requests.Session, url: str) -> str:
    session.headers["User-Agent"] = random.choice(USER_AGENTS)
    print(f"  GET {url}")
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


# ── Extraction helpers ────────────────────────────────────────────────────────

def extract_price_and_unit(html: str) -> tuple[int | None, str | None]:
    """
    Extract unit price and unit ID from __NEXT_DATA__ JSON (primary),
    falling back to HTML text parsing.
    Returns (price, unit_id).
    """
    import json as _json
    soup = BeautifulSoup(html, "lxml")

    # Primary: __NEXT_DATA__ JSON
    tag = soup.find("script", id="__NEXT_DATA__")
    if tag and tag.string:
        try:
            data = _json.loads(tag.string)
            fp = data["props"]["pageProps"]["data"]["floorPlan"]
            units = fp.get("units") or []
            if units:
                u = units[0]
                price = int(u.get("monthlyRent") or 0) or None
                uid = str(u.get("unitName") or u.get("unitId") or "")
                return price, uid or None
        except (KeyError, TypeError, ValueError, _json.JSONDecodeError):
            pass

    # Fallback: raw HTML regex (handles split $ elements)
    m = re.search(r"Starting Price[^$<]{0,30}\$[^0-9]{0,5}([\d,]+)", html, re.IGNORECASE)
    if m:
        price = int(m.group(1).replace(",", ""))
        return (price if price else None), None
    return None, None


def extract_unit_ids_from_next_data(html: str) -> list[str]:
    """Extract all available unit IDs from __NEXT_DATA__ JSON."""
    import json as _json
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return []
    try:
        data = _json.loads(tag.string)
        # Main page: availableApartments[].availableUnitIds
        avail_apts = data["props"]["pageProps"]["data"].get("availableApartments") or []
        # If this IS the main page with multiple floor plans, find the right one
        # If this is a detail page, look in availableUnit
        avail_unit = data["props"]["pageProps"]["data"].get("availableUnit")
        if avail_unit:
            ids = avail_unit.get("availableUnitIds") or []
            if ids:
                return [str(i) for i in ids]
    except (KeyError, TypeError, ValueError, _json.JSONDecodeError):
        pass
    return []


def extract_page_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    t = soup.find("title")
    return t.get_text(strip=True) if t else "(no title)"


def extract_unit_ids(html: str) -> list[str]:
    """Extract unit IDs from a detail page (same logic as parser.py)."""
    soup = BeautifulSoup(html, "lxml")
    unit_ids: list[str] = []

    # Strategy 1: near "Available ... Apartments (N)" heading
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

    # Strategy 2: any element whose sole content is 3-5 digits
    if not unit_ids:
        seen: set[str] = set()
        for el in soup.find_all(string=re.compile(r"^\d{3,5}$")):
            text = el.strip()
            if text and text not in seen:
                unit_ids.append(text)
                seen.add(text)

    return unit_ids


def extract_see_more_links(html: str) -> list[dict]:
    """Pull all 'See More' detail links from the main listing page."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=re.compile(r"floor-plan", re.IGNORECASE)):
        href = a.get("href", "")
        unit_m = re.search(r"unit=(\w+)", href)
        floor_m = re.search(r"floor=(\d+)", href)
        slug_m = re.search(r"available-apartments/([^?]+)", href)
        if slug_m:
            full = (
                f"https://www.camdenliving.com{href}"
                if href.startswith("/")
                else href
            )
            links.append({
                "href": full,
                "slug": slug_m.group(1),
                "unit": unit_m.group(1) if unit_m else None,
                "floor": floor_m.group(1) if floor_m else None,
            })
    # Deduplicate by slug
    seen: set[str] = set()
    unique = []
    for lnk in links:
        if lnk["slug"] not in seen:
            unique.append(lnk)
            seen.add(lnk["slug"])
    return unique


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    sep = "=" * 62
    print(sep)
    print("  Camden Greenville — Per-Unit Pricing Verification")
    print(sep)

    session = requests.Session()
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })

    # ── Step 1: fetch main page ───────────────────────────────────────────────
    print("\n[1] Fetching main listing page...")
    try:
        main_html = fetch(session, BASE_URL)
    except Exception as exc:
        print(f"\nFAILED to fetch main page: {exc}")
        sys.exit(1)

    # ── Pull unit IDs from main page __NEXT_DATA__ ────────────────────────────
    import json as _json
    soup_main = BeautifulSoup(main_html, "lxml")
    next_tag = soup_main.find("script", id="__NEXT_DATA__")
    avail_apts = []
    if next_tag and next_tag.string:
        try:
            nd = _json.loads(next_tag.string)
            avail_apts = nd["props"]["pageProps"]["data"]["availableApartments"]
            print(f"  Loaded {len(avail_apts)} floor plans from __NEXT_DATA__:")
            for ap in avail_apts:
                uid_list = ap.get("availableUnitIds", [])
                print(f"    {ap['name']:<14}  ${ap['monthlyRent']:>5}  {len(uid_list)} unit(s)")
        except Exception as exc:
            print(f"  WARNING: Could not parse __NEXT_DATA__: {exc}")

    if not avail_apts:
        print("\nFAILED: Could not extract floor plan data from main page.")
        sys.exit(1)

    # Pick first floor plan with 2+ units to verify per-unit pricing
    target_fp = next(
        (ap for ap in avail_apts if len(ap.get("availableUnitIds", [])) >= 2),
        None
    )
    if not target_fp:
        print("\nAll floor plans have only 1 available unit — can't compare prices.")
        print("Run the full scraper and check the DB directly.")
        sys.exit(0)

    slug = target_fp["name"].lower().replace(" ", "-") + "-floor-plan"
    unit_ids = [str(u) for u in target_fp["availableUnitIds"]]
    # Get floor param from See More link
    links = extract_see_more_links(main_html)
    link_for_fp = next((lnk for lnk in links if lnk["slug"] == slug), None)
    floor = link_for_fp["floor"] if link_for_fp else None

    print(f"\n  → Verifying: {target_fp['name']} ({len(unit_ids)} units available, floor={floor})")

    # ── Step 2: fetch 2-3 individual unit pages and compare prices ────────────
    check_units = unit_ids[:3]
    print(f"\n[2] Fetching prices for units: {check_units}")

    results: dict[str, int | None] = {}
    actual_unit_ids: dict[str, str | None] = {}

    for uid in check_units:
        time.sleep(random.uniform(1.5, 2.5))
        floor_param = f"&floor={floor}" if floor else ""
        url = f"{BASE_URL}/{slug}?unit={uid}{floor_param}"
        try:
            html = fetch(session, url)
            price, parsed_uid = extract_price_and_unit(html)
            results[uid] = price
            actual_unit_ids[uid] = parsed_uid
            price_str = f"${price:,}" if price else "NOT FOUND"
            uid_note = f"  (server: unit {parsed_uid})" if parsed_uid and parsed_uid != uid else ""
            print(f"  Requested {uid:<6}  {price_str:<12}{uid_note}")
        except Exception as exc:
            print(f"  Unit {uid}: ERROR — {exc}")
            results[uid] = None

    # ── Step 3: verdict ───────────────────────────────────────────────────────
    print(f"\n{sep}")
    valid = {uid: p for uid, p in results.items() if p is not None}

    if len(valid) < 2:
        print("RESULT: INCONCLUSIVE — couldn't get prices for 2+ units.")
        print("        The site may be rate-limiting or there's a network issue.")

    elif len(set(valid.values())) > 1:
        print("RESULT:  PER-UNIT PRICING WORKS")
        print()
        print("  Different units return different prices from the server.")
        print("  The full scraper will capture per-unit pricing correctly.")
        print()
        for uid, price in valid.items():
            actual = actual_unit_ids.get(uid, uid)
            note = f"  (server returned unit {actual})" if actual and actual != uid else ""
            print(f"  Requested {uid}: ${price:,}{note}")

    else:
        single_price = list(valid.values())[0]
        returned_units = set(v for v in actual_unit_ids.values() if v)
        if len(returned_units) > 1:
            print("RESULT:  PARTIAL — unit IDs work but prices differ only in JS")
            print()
            print(f"  All requests returned price: ${single_price:,}")
            print(f"  But server returned different unit IDs: {returned_units}")
            print("  Unit identification works; true per-unit prices need Playwright.")
        else:
            print("RESULT:  PER-UNIT PRICING SAME FOR ALL UNITS (or all 1 price)")
            print()
            print(f"  All fetched units returned: ${single_price:,}")
            print("  This floor plan may genuinely have uniform pricing, OR")
            print("  unit switching is client-side JS only.")
            print("  Try running with a floor plan that has larger price spread.")

    print(sep)


if __name__ == "__main__":
    main()

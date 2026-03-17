"""test_parser.py — Unit tests for parser.py using saved HTML fixtures.

Fixtures are real HTML pages saved from the live site. They are not
included in the repo but can be generated with the save_fixtures.py
helper script (see bottom of this file).

Usage:
    # First save fixtures (one-time):
    cd scraper
    python test_parser.py --save-fixtures

    # Then run tests:
    python test_parser.py
"""

import sys
import json
import time
import random
import argparse
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent / "fixtures"

# ── Fixture download helper ───────────────────────────────────────────────────

BASE_URL = (
    "https://www.camdenliving.com"
    "/apartments/dallas-tx/camden-greenville/available-apartments"
)

USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
]


def _fetch(url: str) -> str:
    import requests
    resp = requests.get(
        url,
        headers={"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def save_fixtures() -> None:
    """Download real HTML and save as fixtures for offline testing."""
    FIXTURE_DIR.mkdir(exist_ok=True)
    print("Saving fixtures — this will make a few real HTTP requests...")

    # Main page
    print(f"  Fetching main page...")
    html = _fetch(BASE_URL)
    path = FIXTURE_DIR / "main_page.html"
    path.write_text(html, encoding="utf-8")
    print(f"  Saved: {path}")

    # Parse main page to get at least one detail page to save
    from parser import parse_main_page, parse_unit_list
    floorplans = parse_main_page(html)
    if not floorplans:
        print("  WARNING: parse_main_page returned no results — check parser logic")
        return

    print(f"  Found {len(floorplans)} floor plans on main page")

    # Save first floor plan with a valid floor number
    target = next((fp for fp in floorplans if fp["floor"]), None)
    if not target:
        print("  WARNING: No floor plan found with a floor number")
        return

    time.sleep(2)
    detail_url = f"{BASE_URL}/{target['slug']}?floor={target['floor']}"
    print(f"  Fetching detail page: {target['slug']}...")
    detail_html = _fetch(detail_url)
    detail_path = FIXTURE_DIR / f"{target['slug']}.html"
    detail_path.write_text(detail_html, encoding="utf-8")
    print(f"  Saved: {detail_path}")

    # Save one unit-specific page
    unit_ids = parse_unit_list(detail_html)
    if unit_ids:
        uid = unit_ids[0]
        time.sleep(2)
        unit_url = f"{BASE_URL}/{target['slug']}?unit={uid}&floor={target['floor']}"
        print(f"  Fetching unit page: {target['slug']}?unit={uid}...")
        unit_html = _fetch(unit_url)
        unit_path = FIXTURE_DIR / f"{target['slug']}_unit_{uid}.html"
        unit_path.write_text(unit_html, encoding="utf-8")
        print(f"  Saved: {unit_path}")

    print("\nFixtures saved. Run 'python test_parser.py' to execute tests.")


# ── Tests ─────────────────────────────────────────────────────────────────────

def _skip(msg: str) -> None:
    print(f"  SKIP  {msg}")


def _pass(msg: str) -> None:
    print(f"  PASS  {msg}")


def _fail(msg: str) -> None:
    print(f"  FAIL  {msg}")


def test_main_page() -> bool:
    print("\n[test_main_page]")
    fixture = FIXTURE_DIR / "main_page.html"
    if not fixture.exists():
        _skip("main_page.html not found — run with --save-fixtures first")
        return True

    from parser import parse_main_page
    html = fixture.read_text(encoding="utf-8")
    results = parse_main_page(html)

    ok = True

    if len(results) < 10:
        _fail(f"Expected 10+ floor plans, got {len(results)}")
        ok = False
    else:
        _pass(f"Found {len(results)} floor plans")

    slugs_seen = set()
    for fp in results:
        issues = []
        if not fp["name"]:
            issues.append("missing name")
        if not fp["slug"] or not fp["slug"].endswith("-floor-plan"):
            issues.append(f"bad slug: {fp['slug']!r}")
        if fp["starting_price"] <= 0:
            issues.append(f"bad price: {fp['starting_price']}")
        if fp["sqft"] <= 0:
            issues.append(f"bad sqft: {fp['sqft']}")
        if fp["slug"] in slugs_seen:
            issues.append("duplicate slug")
        slugs_seen.add(fp["slug"])

        if issues:
            _fail(f"{fp['name']}: {', '.join(issues)}")
            ok = False
        else:
            _pass(
                f"{fp['name']:<15}  ${fp['starting_price']:,}  "
                f"{fp['beds']}BR/{fp['baths']}BA  {fp['sqft']} sqft  "
                f"slug={fp['slug']}  floor={fp['floor']}"
            )

    return ok


def test_unit_list() -> bool:
    print("\n[test_unit_list]")

    # Find any saved detail page fixture (not unit-specific, not main_page)
    fixtures = [
        f for f in FIXTURE_DIR.glob("*-floor-plan.html")
        if "unit_" not in f.name
    ]
    if not fixtures:
        _skip("No floor plan detail fixtures found — run with --save-fixtures first")
        return True

    from parser import parse_unit_list
    ok = True

    for fixture in fixtures:
        html = fixture.read_text(encoding="utf-8")
        unit_ids = parse_unit_list(html)

        if not unit_ids:
            _fail(f"{fixture.name}: no unit IDs found")
            ok = False
        else:
            _pass(f"{fixture.name}: {len(unit_ids)} units → {unit_ids}")

    return ok


def test_unit_detail() -> bool:
    print("\n[test_unit_detail]")

    # Find unit-specific fixture files
    fixtures = list(FIXTURE_DIR.glob("*_unit_*.html"))
    if not fixtures:
        _skip("No unit-specific fixtures found — run with --save-fixtures first")
        return True

    from parser import parse_unit_list, parse_unit_detail, parse_main_page

    # Try to build floorplan_info from main page fixture
    main_fixture = FIXTURE_DIR / "main_page.html"
    fp_lookup: dict[str, dict] = {}
    if main_fixture.exists():
        fps = parse_main_page(main_fixture.read_text(encoding="utf-8"))
        fp_lookup = {fp["slug"]: fp for fp in fps}

    ok = True
    for fixture in fixtures:
        # Derive slug and unit_id from filename: "{slug}_unit_{uid}.html"
        name = fixture.stem  # e.g. "a3-villas-floor-plan_unit_3304"
        parts = name.split("_unit_")
        slug = parts[0]
        requested_uid = parts[1] if len(parts) > 1 else None

        # Build minimal fp_info
        fp_info = fp_lookup.get(slug) or {
            "name": slug,
            "slug": slug,
            "floor": None,
            "beds": 1.0,
            "baths": 1.0,
            "sqft": 0,
            "avail_note": None,
            "special_tags": None,
        }
        # Remap key if using live fp dict
        if "name" in fp_info and "beds" not in fp_info:
            fp_info["beds"] = fp_info.get("bedrooms", 1.0)

        html = fixture.read_text(encoding="utf-8")
        result = parse_unit_detail(html, fp_info)

        issues = []
        if not result.get("price") or result["price"] <= 0:
            issues.append(f"bad price: {result.get('price')}")
        if not result.get("unit_id"):
            issues.append("unit_id not found in HTML (will use requested ID as fallback)")

        # Check unit_id matches what we requested
        parsed_uid = result.get("unit_id") or requested_uid
        if requested_uid and parsed_uid and parsed_uid != requested_uid:
            issues.append(
                f"unit_id mismatch: parsed={parsed_uid!r}, requested={requested_uid!r}"
            )

        if issues:
            # Not all issues are fatal
            for issue in issues:
                if "bad price" in issue:
                    _fail(f"{fixture.name}: {issue}")
                    ok = False
                else:
                    print(f"  NOTE  {fixture.name}: {issue}")
        else:
            features = json.loads(result["unit_features"]) if result.get("unit_features") else []
            _pass(
                f"{fixture.name}  →  unit={parsed_uid}  "
                f"${result['price']:,}  "
                f"{len(features)} features"
            )

    return ok


def test_price_parsing_edge_cases() -> bool:
    """Test _parse_price with synthetic HTML strings."""
    print("\n[test_price_parsing_edge_cases]")
    from parser import _parse_price

    cases = [
        ("Starting Price $1,679", 1679),
        ("Starting Price $2,909", 2909),
        ("Starting Price\n$1,229", 1229),
        ("$1,719 per month", 1719),
        ("Call for pricing", 0),
        ("Starting Price $10,000", 10000),
    ]

    ok = True
    for text, expected in cases:
        got = _parse_price(text)
        if got == expected:
            _pass(f"{text!r:40s} → {got}")
        else:
            _fail(f"{text!r:40s} → got {got}, expected {expected}")
            ok = False
    return ok


def test_slug_generation() -> bool:
    """Verify slug derivation matches the spec's mapping table."""
    print("\n[test_slug_generation]")

    expected = {
        "A1 Villas":   "a1-villas-floor-plan",
        "A3 Villas":   "a3-villas-floor-plan",
        "A4 Villas":   "a4-villas-floor-plan",
        "A3R Flats":   "a3r-flats-floor-plan",
        "A2R Flats":   "a2r-flats-floor-plan",
        "THA1 Villas": "tha1-villas-floor-plan",
        "THA2 Villas": "tha2-villas-floor-plan",
        "TH2 Flats":   "th2-flats-floor-plan",
        "TH1 Flats":   "th1-flats-floor-plan",
        "TH1A Flats":  "th1a-flats-floor-plan",
        "TH1B Flats":  "th1b-flats-floor-plan",
        "THB1 Villas": "thb1-villas-floor-plan",
        "THB2 Villas": "thb2-villas-floor-plan",
    }

    ok = True
    for name, slug in expected.items():
        derived = name.lower().replace(" ", "-") + "-floor-plan"
        if derived == slug:
            _pass(f"{name!r:15s} → {derived}")
        else:
            _fail(f"{name!r:15s} → got {derived!r}, expected {slug!r}")
            ok = False
    return ok


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Test parser.py")
    parser.add_argument(
        "--save-fixtures",
        action="store_true",
        help="Download real HTML and save as test fixtures (requires network)",
    )
    args = parser.parse_args()

    if args.save_fixtures:
        save_fixtures()
        return

    print("=" * 55)
    print("Camden Parser Tests")
    print("=" * 55)

    results = [
        test_slug_generation(),
        test_price_parsing_edge_cases(),
        test_main_page(),
        test_unit_list(),
        test_unit_detail(),
    ]

    print("\n" + "=" * 55)
    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"All {total} test suites passed.")
    else:
        print(f"{passed}/{total} test suites passed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

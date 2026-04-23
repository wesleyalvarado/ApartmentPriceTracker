#!/usr/bin/env python3
"""
SkyHouse Dallas scraper — current site structure (simpsonpropertygroup.com).

Data flow:
  Phase 1: Floor plans page → floor plan IDs, bed/bath/sqft, price range
           (data-* attrs on .floorplanbox elements)
  Phase 2: Per-floor-plan HTMX detail page → individual unit IDs, per-unit price,
           availability date, floor number
           (GET ?handler=FloorPlanView&floorPlanId=N&communityId=76, HX-Request: true)

Run:
    cd scraper/skyhouse_dallas && python scraper.py
"""

import logging
import random
import re
import sqlite3
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

COMPLEX_SLUG   = "skyhouse_dallas"
COMPLEX_NAME   = "SkyHouse Dallas"
COMPLEX_CITY   = "Dallas"
COMPLEX_STATE  = "TX"
COMMUNITY_ID   = 76
BASE_URL       = (
    "https://www.simpsonpropertygroup.com/apartments/dallas-texas"
    "/skyhouse-dallas-victory-park-downtown/apartment-floor-plans"
)

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "apartments.db"

USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
    ),
]

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── HTTP ──────────────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": BASE_URL,
    })
    return s


def fetch(session: requests.Session, url: str, extra_headers: dict | None = None,
          retries: int = 3) -> str:
    session.headers["User-Agent"] = random.choice(USER_AGENTS)
    headers = dict(session.headers)
    if extra_headers:
        headers.update(extra_headers)
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"All {retries} attempts failed for {url}")

# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_floor_plans(html: str) -> list[dict]:
    """
    Parse floor plan metadata from the main floor plans page.
    Data is stored in data-* attributes on .floorplanbox elements.
    """
    soup = BeautifulSoup(html, "lxml")
    plans = soup.find_all("div", attrs={"data-floorplanid": True})
    results = []
    for p in plans:
        fp_id = p.get("data-floorplanid")
        name  = p.get("data-name", "")
        beds  = int(p.get("data-beds", 0) or 0)
        available = p.get("data-available-units", "false").lower() == "true"

        # Min rent (use as starting price)
        minrent_raw = p.get("data-minrent", "0")
        try:
            min_rent = int(float(minrent_raw))
        except (ValueError, TypeError):
            min_rent = 0

        # Parse sqft and baths from visible text
        text = p.get_text(separator=" ", strip=True)
        sqft = _parse_sqft(text)
        baths = _parse_baths(text)

        # Available date
        avail_date = p.get("data-dateavail", "") or None

        if not fp_id or not name:
            continue

        results.append({
            "fp_id":        int(fp_id),
            "name":         name,
            "slug":         re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
            "beds":         beds,
            "baths":        baths,
            "sqft":         sqft,
            "min_rent":     min_rent,
            "avail_date":   avail_date,
            "available":    available,
        })

    return results


def parse_units_from_detail(html: str, fp: dict, complex_id: int) -> list[dict]:
    """
    Parse individual units from the HTMX floor plan detail page.
    Unit cards have data-testid="floorplan-unit-card".
    """
    soup = BeautifulSoup(html, "lxml")
    cards = soup.find_all(attrs={"data-testid": "floorplan-unit-card"})
    results = []

    for card in cards:
        unit_id  = card.get("data-unitid", "")   # internal ID (e.g. 151340)
        unit_no  = card.get("data-unitno", "")   # apt number (e.g. 609)

        text = card.get_text(separator=" ", strip=True)

        # Extract base rent: "Base Rent $1,570"
        price_m = re.search(r"Base Rent\s*\$([\d,]+)", text)
        price = int(price_m.group(1).replace(",", "")) if price_m else 0

        if not price:
            continue

        # Extract availability: "Available Now" or "Available MM/DD/YYYY"
        avail_m = re.search(r"Available\s+(Now|[\d/]+)", text)
        avail_raw = avail_m.group(1) if avail_m else ""
        available_date = _parse_avail_date(avail_raw)

        # Floor from amenities tooltip: "data-amenities="6th Floor""
        floor_btn = card.find(attrs={"data-amenities": True})
        floor = None
        if floor_btn:
            amenity = floor_btn.get("data-amenities", "")
            floor_m = re.search(r"(\d+)(?:st|nd|rd|th)\s+[Ff]loor", amenity)
            if floor_m:
                floor = int(floor_m.group(1))

        # Fallback: infer floor from unit number (e.g. 609 → 6, 1709 → 17)
        if floor is None and unit_no.isdigit():
            n = int(unit_no)
            floor = n // 100

        results.append({
            "complex_id":     complex_id,
            "unit_id":        unit_no or unit_id,
            "floorplan_name": fp["name"],
            "floorplan_slug": fp["slug"],
            "floor":          floor,
            "bedrooms":       fp["beds"],
            "bathrooms":      fp["baths"],
            "sqft":           fp["sqft"],
            "price":          price,
            "available_date": available_date,
            "avail_note":     "Available Now" if not available_date else None,
            "special_tags":   None,
            "unit_features":  None,
        })

    return results


def _parse_sqft(text: str) -> int:
    m = re.search(r"([\d,]+)\s*Sq\s*Ft", text, re.IGNORECASE)
    if m:
        return int(m.group(1).replace(",", ""))
    # Range: "1318 - 1412 Sq Ft" → take smaller
    m = re.search(r"([\d,]+)\s*-\s*[\d,]+\s*Sq\s*Ft", text, re.IGNORECASE)
    return int(m.group(1).replace(",", "")) if m else 0


def _parse_baths(text: str) -> float:
    m = re.search(r"([\d.]+)\s*Bath", text, re.IGNORECASE)
    return float(m.group(1)) if m else 1.0


def _parse_avail_date(raw: str) -> str | None:
    """'Now' → None (available today), 'MM/DD/YYYY' → 'YYYY-MM-DD'."""
    if not raw or raw.strip().lower() in ("now", ""):
        return None
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw.strip())
    if m:
        mo, day, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{yr}-{mo:02d}-{day:02d}"
    return None

# ── DB ────────────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_complex(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT id FROM complexes WHERE name=?", (COMPLEX_SLUG,)
    ).fetchone()
    if row:
        return row[0]
    conn.execute(
        """INSERT INTO complexes (name, display_name, city, state, url, community_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (COMPLEX_SLUG, COMPLEX_NAME, COMPLEX_CITY, COMPLEX_STATE, BASE_URL, COMMUNITY_ID),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM complexes WHERE name=?", (COMPLEX_SLUG,)).fetchone()
    log.info("Registered complex '%s' id=%d", COMPLEX_SLUG, row[0])
    return row[0]


def upsert_floorplan_meta(conn: sqlite3.Connection, complex_id: int, fp: dict, ts: str) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO floorplan_meta
               (complex_id, floorplan_name, floorplan_slug, floor,
                bedrooms, bathrooms, sqft, special_tags, image_url, last_updated)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (complex_id, fp["name"], fp["slug"], None,
         fp["beds"], fp["baths"], fp["sqft"], None, None, ts),
    )


def insert_snapshot(conn: sqlite3.Connection, unit: dict, ts: str) -> None:
    if not unit.get("price") or unit["price"] <= 0:
        return
    existing = conn.execute(
        "SELECT id, price FROM price_snapshots WHERE complex_id=? AND unit_id=? AND DATE(scraped_at)=DATE(?)",
        (unit["complex_id"], unit["unit_id"], ts),
    ).fetchone()
    if existing:
        if existing[1] != unit["price"]:
            conn.execute(
                """UPDATE price_snapshots
                   SET price=?, scraped_at=?, available_date=?, avail_note=?
                   WHERE id=?""",
                (unit["price"], ts, unit.get("available_date"), unit.get("avail_note"), existing[0]),
            )
        return
    conn.execute(
        """INSERT INTO price_snapshots
               (scraped_at, complex_id, floorplan_name, floorplan_slug, unit_id, floor,
                bedrooms, bathrooms, sqft, price, available_date, avail_note,
                special_tags, unit_features)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ts, unit["complex_id"], unit["floorplan_name"], unit["floorplan_slug"],
            unit["unit_id"], unit.get("floor"),
            unit["bedrooms"], unit["bathrooms"], unit["sqft"], unit["price"],
            unit.get("available_date"), unit.get("avail_note"),
            unit.get("special_tags"), unit.get("unit_features"),
        ),
    )

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log.info("═" * 55)
    log.info("SkyHouse Dallas scrape started  %s", ts)
    log.info("═" * 55)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    complex_id = ensure_complex(conn)

    session = _make_session()

    # ── Phase 1: Floor plans page ─────────────────────────────────────────────
    log.info("[Phase 1] Fetching floor plans page...")
    try:
        main_html = fetch(session, BASE_URL)
    except RuntimeError as exc:
        log.error("Could not fetch floor plans page: %s", exc)
        conn.close()
        sys.exit(1)

    floor_plans = parse_floor_plans(main_html)
    log.info("[Phase 1] Found %d floor plans:", len(floor_plans))
    for fp in floor_plans:
        status = "available" if fp["available"] else "unavailable"
        log.info(
            "  %-20s  id=%-5d  %sBR/%.1fBA  %d sqft  $%s  [%s]",
            fp["name"], fp["fp_id"], fp["beds"], fp["baths"], fp["sqft"],
            f"{fp['min_rent']:,}" if fp["min_rent"] else "N/A",
            status,
        )
        upsert_floorplan_meta(conn, complex_id, fp, ts)
    conn.commit()

    # ── Phase 2: Per-floor-plan unit details ─────────────────────────────────
    log.info("[Phase 2] Fetching unit details per available floor plan...")
    all_units: list[dict] = []
    http_requests = 1

    available_fps = [fp for fp in floor_plans if fp["available"]]
    log.info("  %d floor plans have available units", len(available_fps))

    for fp in available_fps:
        time.sleep(random.uniform(1.5, 3.0))
        detail_url = (
            f"{BASE_URL}?handler=FloorPlanView"
            f"&floorPlanId={fp['fp_id']}&communityId={COMMUNITY_ID}"
        )
        try:
            detail_html = fetch(session, detail_url, extra_headers={"HX-Request": "true"})
            http_requests += 1
            units = parse_units_from_detail(detail_html, fp, complex_id)
            if units:
                prices = sorted(set(u["price"] for u in units))
                log.info(
                    "  %-20s — %d unit(s)  $%s–$%s",
                    fp["name"], len(units),
                    f"{prices[0]:,}", f"{prices[-1]:,}",
                )
                all_units.extend(units)
            else:
                log.warning("  %-20s — no units parsed from detail page", fp["name"])
        except RuntimeError as exc:
            log.warning("  %-20s — detail fetch failed: %s", fp["name"], exc)

    # ── Insert ────────────────────────────────────────────────────────────────
    for unit in all_units:
        insert_snapshot(conn, unit, ts)
    conn.commit()
    conn.close()

    log.info("═" * 55)
    log.info(
        "Done. %d units across %d floor plans  (%d HTTP requests)",
        len(all_units), len(available_fps), http_requests,
    )
    log.info("DB: %s", DB_PATH)
    log.info("═" * 55)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
SkyHouse Dallas scraper.

Data source: simpsonpropertygroup.com floor-plans page.
- Floor plan metadata: `var communityPlans = [...]` JS blob
- Unit availability:   `<div id="sorted_units">` with data-* attrs
- SecureCafe UnitID / FloorPlanID: extracted from RentalOptions links per unit

Run:
    cd scraper/skyhouse_dallas && python scraper.py
"""

import json
import logging
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

COMPLEX_SLUG   = "skyhouse_dallas"
COMPLEX_NAME   = "SkyHouse Dallas - Victory Park"
COMPLEX_CITY   = "Dallas"
COMPLEX_STATE  = "TX"
COMPLEX_URL    = (
    "https://www.simpsonpropertygroup.com/apartments/dallas-texas/"
    "skyhouse-dallas-victory-park-downtown/apartment-floor-plans"
)
PROPERTY_ID    = "210946"   # Yardi / RentCafe propertyId

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "camden_prices.db"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
}

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_complex(conn: sqlite3.Connection) -> int:
    """Insert complex row if needed, return complex_id."""
    row = conn.execute(
        "SELECT id FROM complexes WHERE name=?", (COMPLEX_SLUG,)
    ).fetchone()
    if row:
        return row[0]
    conn.execute(
        """
        INSERT INTO complexes (name, display_name, city, state, url, community_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (COMPLEX_SLUG, COMPLEX_NAME, COMPLEX_CITY, COMPLEX_STATE, COMPLEX_URL, PROPERTY_ID),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM complexes WHERE name=?", (COMPLEX_SLUG,)
    ).fetchone()
    log.info("Created complex '%s' with id=%d", COMPLEX_SLUG, row[0])
    return row[0]


def upsert_floorplan_meta(conn: sqlite3.Connection, complex_id: int, fp: dict, ts: str) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO floorplan_meta
            (complex_id, floorplan_name, floorplan_slug, floor,
             bedrooms, bathrooms, sqft, special_tags, image_url, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            complex_id,
            fp["name"],
            re.sub(r"[^a-z0-9]+", "-", fp["name"].lower()).strip("-"),
            None,
            fp["beds"],
            fp["baths"],
            fp["sqft"],
            None,
            fp.get("image_url"),
            ts,
        ),
    )


def insert_snapshot(conn: sqlite3.Connection, unit: dict, ts: str) -> None:
    existing = conn.execute(
        "SELECT id, price FROM price_snapshots WHERE unit_id=? AND DATE(scraped_at)=DATE(?)",
        (unit["unit_id"], ts),
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
        """
        INSERT INTO price_snapshots
            (scraped_at, complex_id, floorplan_name, floorplan_slug, unit_id, floor,
             bedrooms, bathrooms, sqft, price,
             available_date, avail_note, special_tags, unit_features)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ts,
            unit["complex_id"],
            unit["floorplan_name"],
            unit["floorplan_slug"],
            unit["unit_id"],
            unit.get("floor"),
            unit["bedrooms"],
            unit["bathrooms"],
            unit["sqft"],
            unit["price"],
            unit.get("available_date"),
            unit.get("avail_note"),
            unit.get("special_tags"),
            unit.get("unit_features"),
        ),
    )

# ── Parsing ───────────────────────────────────────────────────────────────────

def fetch_page() -> str:
    log.info("Fetching %s", COMPLEX_URL)
    r = requests.get(COMPLEX_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    log.info("Page fetched — %d bytes", len(r.text))
    return r.text


def parse_community_plans(html: str) -> dict:
    """Return dict of {plan_name: {beds, baths, sqft}} from communityPlans JS blob."""
    m = re.search(r"var communityPlans\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not m:
        log.warning("communityPlans JS blob not found")
        return {}
    plans = json.loads(m.group(1))
    result = {}
    for p in plans:
        name = p.get("Name", "")
        layouts = p.get("Layouts") or []
        image_url = layouts[0].get("ImageURL") if layouts else None
        result[name] = {
            "beds": int(p.get("NumBeds", 0)),
            "baths": float(p.get("NumBaths", 1)),
            "sqft": int(p.get("MinSqFt", 0)),
            "image_url": image_url,
        }
    log.info("Parsed %d floor plans from communityPlans", len(result))
    return result


def parse_units(html: str, fp_meta: dict, complex_id: int, ts: str) -> list[dict]:
    """Parse all available units from #sorted_units div."""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("div", {"id": "sorted_units"})
    if not container:
        log.error("#sorted_units div not found")
        return []

    units = []
    for div in container.find_all("div", class_="unit"):
        try:
            unit_no  = div.get("data-unitno", "")
            unit_id  = div.get("data-unitid", unit_no)
            fp_name  = div.get("data-floorplan", "Unknown")
            beds     = int(float(div.get("data-beds", 0)))
            min_rent = float(div.get("data-minrent", 0) or 0)
            sqft     = int(float(div.get("data-sqft", 0) or 0))
            date_str = div.get("data-dateavail", "")

            if not min_rent:
                continue

            # Infer floor from unit number (e.g. 1609 → 16, 412 → 4)
            floor = int(unit_no) // 100 if unit_no.isdigit() else None

            # Baths from communityPlans meta; fallback to inner text
            baths = fp_meta.get(fp_name, {}).get("baths", 1.0)

            # Availability date
            avail_date = _parse_avail_date(date_str)
            avail_note = "Available Now" if not avail_date else None

            # SecureCafe UnitID + FloorPlanID from the RentalOptions link
            sc_link = div.find("a", href=re.compile(r"RentalOptions", re.I))
            sc_unit_id  = None
            sc_fp_id    = None
            if sc_link:
                href = sc_link.get("href", "")
                m_uid = re.search(r"UnitID=(\d+)", href)
                m_fid = re.search(r"FloorPlanID=(\d+)", href)
                sc_unit_id = m_uid.group(1) if m_uid else None
                sc_fp_id   = m_fid.group(1) if m_fid else None

            units.append({
                "complex_id":     complex_id,
                "unit_id":        unit_no,        # human-readable apt number
                "rentcafe_unit_id": unit_id,      # RentCafe internal ID (data-unitid)
                "sc_unit_id":     sc_unit_id,     # SecureCafe UnitID (for lease terms)
                "sc_fp_id":       sc_fp_id,       # SecureCafe FloorPlanID
                "floorplan_name": fp_name,
                "floorplan_slug": re.sub(r"[^a-z0-9]+", "-", fp_name.lower()).strip("-"),
                "floor":          floor,
                "bedrooms":       beds,
                "bathrooms":      baths,
                "sqft":           sqft,
                "price":          int(min_rent),
                "available_date": avail_date,
                "avail_note":     avail_note,
                "special_tags":   None,
                "unit_features":  None,
            })
        except Exception as e:
            log.warning("Skipping unit — %s", e)

    log.info("Parsed %d available units", len(units))
    return units


def _parse_avail_date(date_str: str) -> str | None:
    """Convert '3/17/2026 12:00:00 AM' → '2026-03-17', or None if unavailable/past."""
    if not date_str:
        return None
    try:
        m = re.match(r"(\d+)/(\d+)/(\d+)", date_str)
        if m:
            month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f"{year}-{month:02d}-{day:02d}"
    except Exception:
        pass
    return None

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log.info("═" * 55)
    log.info("SkyHouse Dallas scrape started  %s", ts)
    log.info("═" * 55)

    html = fetch_page()

    fp_meta = parse_community_plans(html)
    conn    = get_db()
    complex_id = ensure_complex(conn)

    # Upsert floor plan metadata
    for name, meta in fp_meta.items():
        upsert_floorplan_meta(conn, complex_id, {"name": name, **meta}, ts)
    conn.commit()

    units = parse_units(html, fp_meta, complex_id, ts)

    inserted = 0
    for u in units:
        insert_snapshot(conn, u, ts)
        inserted += 1

    conn.commit()
    conn.close()

    log.info("═" * 55)
    log.info("Done. %d units across %d floor plans", len(units), len(fp_meta))
    log.info("DB: %s", DB_PATH)
    log.info("═" * 55)


if __name__ == "__main__":
    main()

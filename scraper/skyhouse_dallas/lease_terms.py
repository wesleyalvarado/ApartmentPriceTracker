#!/usr/bin/env python3
"""
SkyHouse Dallas — lease-term pricing (4, 5, 6 month).

For each available unit in today's price_snapshots, POSTs to SecureCafe's
RentalOptions endpoint with each lease term to get the per-term rent.

Depends on scraper.py having already been run today (needs sc_unit_id /
sc_fp_id stored in the snapshot rows via the scraper's unit dicts).

Because price_snapshots doesn't store sc_unit_id, this script re-fetches
the Simpson page to rebuild the unit→SecureCafe mapping.

Run:
    cd scraper/skyhouse_dallas && python lease_terms.py
"""

import logging
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

COMPLEX_SLUG  = "skyhouse_dallas"
PROPERTY_ID   = "210946"
LEASE_TERMS   = [4, 5, 6]

SIMPSON_URL   = (
    "https://www.simpsonpropertygroup.com/apartments/dallas-texas/"
    "skyhouse-dallas-victory-park-downtown/apartment-floor-plans"
)
SC_BASE_URL   = (
    "https://skyhousedallas.securecafe.com/onlineleasing/"
    "skyhouse-dallas/oleapplication.aspx"
)

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "camden_prices.db"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}

DELAY = 1.5   # seconds between requests

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


def get_complex_id(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT id FROM complexes WHERE name=?", (COMPLEX_SLUG,)
    ).fetchone()
    if not row:
        raise RuntimeError(f"Complex '{COMPLEX_SLUG}' not found — run scraper.py first")
    return row[0]


def get_todays_units(conn: sqlite3.Connection, complex_id: int) -> list[dict]:
    """Return today's price_snapshots rows for this complex."""
    rows = conn.execute(
        """
        SELECT unit_id, floorplan_name
        FROM price_snapshots
        WHERE complex_id=? AND DATE(scraped_at)=DATE('now')
        """,
        (complex_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def insert_lease_term_price(conn: sqlite3.Connection, rec: dict) -> None:
    existing = conn.execute(
        """SELECT id, monthly_rent FROM lease_term_prices
           WHERE unit_id=? AND lease_months=? AND DATE(scraped_at)=DATE(?)""",
        (rec["unit_id"], rec["lease_months"], rec["scraped_at"]),
    ).fetchone()
    if existing:
        if existing[1] != rec["monthly_rent"]:
            conn.execute(
                "UPDATE lease_term_prices SET monthly_rent=?, total_cost=?, scraped_at=? WHERE id=?",
                (rec["monthly_rent"], rec.get("total_cost"), rec["scraped_at"], existing[0]),
            )
        return
    conn.execute(
        """
        INSERT INTO lease_term_prices
            (scraped_at, complex_id, unit_id, floorplan_name, move_in_date,
             lease_months, monthly_rent, total_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rec["scraped_at"],
            rec["complex_id"],
            rec["unit_id"],
            rec["floorplan_name"],
            rec.get("move_in_date") or "",
            rec["lease_months"],
            rec["monthly_rent"],
            rec.get("total_cost"),
        ),
    )

# ── Page parsing ──────────────────────────────────────────────────────────────

def build_unit_sc_map(html: str) -> dict:
    """
    Returns {unit_no: {sc_unit_id, sc_fp_id}} for all units on the page.
    unit_no matches price_snapshots.unit_id (the apartment number string).
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("div", {"id": "sorted_units"})
    if not container:
        raise RuntimeError("#sorted_units div not found on page")

    mapping = {}
    for div in container.find_all("div", class_="unit"):
        unit_no = div.get("data-unitno", "")
        sc_link = div.find("a", href=re.compile(r"RentalOptions", re.I))
        if not sc_link:
            continue
        href = sc_link.get("href", "")
        m_uid = re.search(r"UnitID=(\d+)", href)
        m_fid = re.search(r"FloorPlanID=(\d+)", href)
        if m_uid and m_fid:
            mapping[unit_no] = {
                "sc_unit_id": m_uid.group(1),
                "sc_fp_id":   m_fid.group(1),
            }
    return mapping

# ── SecureCafe pricing ────────────────────────────────────────────────────────

def fetch_term_rent(sc_unit_id: str, sc_fp_id: str, term: int) -> int | None:
    """POST to SecureCafe and return base rent for the given lease term, or None."""
    url = (
        f"{SC_BASE_URL}"
        f"?stepname=RentalOptions&myOlePropertyId={PROPERTY_ID}"
        f"&FloorPlanID={sc_fp_id}&UnitID={sc_unit_id}&header=1"
    )
    form = {
        "sLeaseTerm":       str(term),
        "UnitId":           sc_unit_id,
        "FloorplanId":      sc_fp_id,
        "myOlePropertyId":  PROPERTY_ID,
    }
    try:
        r = requests.post(
            url, data=form,
            headers={**HEADERS, "Referer": "https://skyhousedallas.securecafe.com/",
                     "Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
        r.raise_for_status()
        # Parse BaseRent hidden input — most reliable extraction point
        m = re.search(
            r'name=["\']BaseRent["\'][^>]*value=["\']([^"\']+)["\']', r.text
        )
        if not m:
            m = re.search(
                r'value=["\']([^"\']+)["\'][^>]*name=["\']BaseRent["\']', r.text
            )
        if m:
            return int(float(m.group(1)))
    except Exception as e:
        log.warning("SecureCafe error (unit=%s term=%s): %s", sc_unit_id, term, e)
    return None

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log.info("═" * 55)
    log.info("SkyHouse Dallas lease-term pricing  %s", ts)
    log.info("Desired terms: %s months", LEASE_TERMS)
    log.info("═" * 55)

    conn       = get_db()
    complex_id = get_complex_id(conn)
    units      = get_todays_units(conn, complex_id)

    if not units:
        log.warning("No units in today's price_snapshots — run scraper.py first")
        conn.close()
        return

    log.info("Found %d units in today's snapshots", len(units))

    # Build SecureCafe ID map from the Simpson page
    log.info("Fetching Simpson page for SecureCafe ID mapping...")
    html = requests.get(SIMPSON_URL, headers=HEADERS, timeout=30).text
    sc_map = build_unit_sc_map(html)
    log.info("SecureCafe map built for %d units", len(sc_map))

    total_written = 0
    term_counts   = {t: 0 for t in LEASE_TERMS}

    for i, unit in enumerate(units, 1):
        apt_no   = unit["unit_id"]
        fp_name  = unit["floorplan_name"]
        sc_info  = sc_map.get(apt_no)

        log.info("[%d/%d] Apt #%s  (%s)", i, len(units), apt_no, fp_name)

        if not sc_info:
            log.warning("  No SecureCafe mapping for Apt #%s — skipping", apt_no)
            continue

        sc_unit_id = sc_info["sc_unit_id"]
        sc_fp_id   = sc_info["sc_fp_id"]
        rents = {}

        for term in LEASE_TERMS:
            time.sleep(DELAY)
            rent = fetch_term_rent(sc_unit_id, sc_fp_id, term)
            if rent:
                rents[term] = rent
                rec = {
                    "scraped_at":   ts,
                    "complex_id":   complex_id,
                    "unit_id":      apt_no,
                    "floorplan_name": fp_name,
                    "move_in_date": "",
                    "lease_months": term,
                    "monthly_rent": rent,
                    "total_cost":   rent * term,
                }
                insert_lease_term_price(conn, rec)
                term_counts[term] += 1
                total_written += 1

        if rents:
            parts = "  ".join(f"{t}mo=${r:,}" for t, r in rents.items())
            log.info("  %s", parts)
        else:
            log.warning("  No rent data returned")

    conn.commit()

    log.info("─" * 55)
    log.info("Wrote %d records to lease_term_prices", total_written)
    for term in LEASE_TERMS:
        log.info("  %d-month: %d units", term, term_counts[term])
    log.info("═" * 55)
    log.info("Done. DB: %s", DB_PATH)
    log.info("═" * 55)

    conn.close()


if __name__ == "__main__":
    main()

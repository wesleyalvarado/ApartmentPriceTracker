"""scraper.py — Main entry point for Camden Greenville price tracker.

Orchestrates two-phase scraping:
  Phase 1: main listing page → all floor plans + detail URLs
  Phase 2: per-floor-plan detail pages → all unit IDs + per-unit prices

Writes results to SQLite at data/camden_prices.db.

Usage:
    cd scraper
    python scraper.py
"""

import csv
import sys
import time
import random
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

from parser import parse_main_page, parse_unit_list, parse_unit_detail, parse_all_units_from_detail, build_avail_note

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent.parent  # AptPricing/
DB_PATH = ROOT / "data" / "camden_prices.db"
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"

COMPLEX_ID = 1  # Camden Greenville — see complexes table

BASE_URL = (
    "https://www.camdenliving.com"
    "/apartments/dallas-tx/camden-greenville/available-apartments"
)

# ── HTTP config ───────────────────────────────────────────────────────────────

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
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.3 Safari/605.1.15"
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

# ── Database schema ───────────────────────────────────────────────────────────

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS complexes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    display_name TEXT    NOT NULL,
    city         TEXT    NOT NULL,
    state        TEXT    NOT NULL DEFAULT 'TX',
    url          TEXT,
    community_id INTEGER,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO complexes
    (id, name, display_name, city, state, url, community_id, created_at)
VALUES
    (1, 'camden-greenville', 'Camden Greenville', 'Dallas', 'TX',
     'https://www.camdenliving.com/apartments/dallas-tx/camden-greenville',
     4877024, datetime('now'));

CREATE TABLE IF NOT EXISTS price_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scraped_at      TEXT    NOT NULL,
    complex_id      INTEGER NOT NULL DEFAULT 1,
    floorplan_name  TEXT    NOT NULL,
    floorplan_slug  TEXT    NOT NULL,
    unit_id         TEXT    NOT NULL,
    floor           INTEGER,
    bedrooms        REAL    NOT NULL,
    bathrooms       REAL    NOT NULL,
    sqft            INTEGER NOT NULL,
    price           INTEGER NOT NULL,
    available_date  TEXT,
    avail_note      TEXT,
    special_tags    TEXT,
    unit_features   TEXT
);

CREATE INDEX IF NOT EXISTS idx_unit_time
    ON price_snapshots(unit_id, scraped_at);
CREATE INDEX IF NOT EXISTS idx_floorplan_time
    ON price_snapshots(floorplan_name, scraped_at);
CREATE INDEX IF NOT EXISTS idx_scraped_at
    ON price_snapshots(scraped_at);
CREATE INDEX IF NOT EXISTS idx_bedrooms
    ON price_snapshots(bedrooms);
CREATE INDEX IF NOT EXISTS idx_complex_id
    ON price_snapshots(complex_id);

CREATE TABLE IF NOT EXISTS floorplan_meta (
    complex_id      INTEGER NOT NULL DEFAULT 1,
    floorplan_name  TEXT    NOT NULL,
    floorplan_slug  TEXT    NOT NULL,
    floor           INTEGER,
    bedrooms        REAL    NOT NULL,
    bathrooms       REAL    NOT NULL,
    sqft            INTEGER NOT NULL,
    special_tags    TEXT,
    last_updated    TEXT    NOT NULL,
    PRIMARY KEY (complex_id, floorplan_name)
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_id      INTEGER NOT NULL DEFAULT 1,
    floorplan_name  TEXT,
    unit_id         TEXT,
    max_price       INTEGER NOT NULL,
    active          INTEGER DEFAULT 1,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS lease_term_prices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scraped_at      TEXT    NOT NULL,
    complex_id      INTEGER NOT NULL DEFAULT 1,
    unit_id         TEXT    NOT NULL,
    floorplan_name  TEXT    NOT NULL,
    move_in_date    TEXT    NOT NULL,
    lease_months    INTEGER NOT NULL,
    monthly_rent    INTEGER NOT NULL,
    total_cost      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_lt_complex
    ON lease_term_prices(complex_id);
"""


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    })
    return session


def fetch(session: requests.Session, url: str, retries: int = 3) -> str:
    """Fetch a URL with retry/back-off and a random User-Agent."""
    for attempt in range(1, retries + 1):
        session.headers["User-Agent"] = random.choice(USER_AGENTS)
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"All {retries} attempts failed for {url}")


# ── Snapshot helpers ──────────────────────────────────────────────────────────

def save_snapshot(html: str, name: str, timestamp: str) -> None:
    """Persist raw HTML to data/snapshots/ for later re-parsing."""
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_ts = timestamp.replace(":", "-").replace(".", "-")
    path = SNAPSHOTS_DIR / f"{safe_ts}_{name}.html"
    path.write_text(html, encoding="utf-8")
    log.debug("Saved snapshot: %s", path.name)


# ── Database helpers ──────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_floorplan_meta(conn: sqlite3.Connection, fp: dict, ts: str) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO floorplan_meta
            (complex_id, floorplan_name, floorplan_slug, floor,
             bedrooms, bathrooms, sqft, special_tags, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            COMPLEX_ID,
            fp["name"], fp["slug"], fp["floor"],
            fp["beds"], fp["baths"], fp["sqft"],
            fp.get("special_tags"), ts,
        ),
    )


def insert_snapshot(conn: sqlite3.Connection, unit: dict, ts: str) -> None:
    if not unit.get("price") or unit["price"] <= 0:
        log.warning("Skipping unit %s — no valid price", unit.get("unit_id"))
        return
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
            unit.get("complex_id", COMPLEX_ID),
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


def _fallback_unit(fp: dict) -> dict | None:
    """Build a unit record from the floor plan's starting price (fallback)."""
    if not fp.get("default_unit_id") or not fp.get("starting_price", 0):
        return None
    return {
        "floorplan_name": fp["name"],
        "floorplan_slug": fp["slug"],
        "unit_id": fp["default_unit_id"],
        "floor": fp["floor"],
        "bedrooms": fp["beds"],
        "bathrooms": fp["baths"],
        "sqft": fp["sqft"],
        "price": fp["starting_price"],
        "available_date": fp.get("available_date"),
        "avail_note": fp.get("avail_note"),
        "special_tags": fp.get("special_tags"),
        "unit_features": None,
    }


# ── CSV export ───────────────────────────────────────────────────────────────

CSV_COLUMNS = [
    "scraped_at", "floorplan_name", "unit_id", "floor",
    "bedrooms", "bathrooms", "sqft", "price",
    "available_date", "avail_note", "special_tags",
]


def export_csvs(conn: sqlite3.Connection, ts: str) -> None:
    """
    Write two CSV files after each scrape:

    latest.csv  — current snapshot only (overwritten each run).
                  One row per unit, sorted cheapest first.
                  Easy to open in Excel / Numbers right now.

    history.csv — full append-only log of every scrape ever run.
                  One row per unit per scrape.  Grows over time.
    """
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # ── latest.csv (current scrape only, overwrite) ──────────────────────────
    latest_rows = conn.execute(
        f"""
        SELECT {', '.join(CSV_COLUMNS)}
        FROM price_snapshots
        WHERE scraped_at = ?
        ORDER BY price ASC, floorplan_name, unit_id
        """,
        (ts,),
    ).fetchall()

    latest_path = data_dir / "latest.csv"
    with latest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        writer.writerows(latest_rows)
    log.info("Wrote %d rows → %s", len(latest_rows), latest_path)

    # ── history.csv (append — never overwrite) ───────────────────────────────
    history_path = data_dir / "history.csv"
    write_header = not history_path.exists()
    with history_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(CSV_COLUMNS)
        writer.writerows(latest_rows)
    log.info("Appended %d rows → %s", len(latest_rows), history_path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log.info("═" * 55)
    log.info("Camden Greenville scrape started  %s", ts)
    log.info("═" * 55)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    session = _make_session()

    # ── Phase 1: Main listing page ────────────────────────────────────────────
    log.info("[Phase 1] Fetching main listing page...")
    try:
        main_html = fetch(session, BASE_URL)
    except RuntimeError as exc:
        log.error("Could not fetch main page: %s", exc)
        conn.close()
        sys.exit(1)

    save_snapshot(main_html, "main", ts)
    floorplans = parse_main_page(main_html)

    if not floorplans:
        log.error(
            "No floor plans found on main page — "
            "the site's HTML structure may have changed. "
            "Check data/snapshots/ for the raw HTML."
        )
        conn.close()
        sys.exit(1)

    log.info("[Phase 1] Found %d floor plans:", len(floorplans))
    for fp in floorplans:
        log.info(
            "  %-15s  $%s  %sBR  slug=%s  floor=%s",
            fp["name"],
            f"{fp['starting_price']:,}" if fp["starting_price"] else "N/A",
            fp["beds"],
            fp["slug"],
            fp["floor"],
        )
        upsert_floorplan_meta(conn, fp, ts)
    conn.commit()

    # ── Phase 2: Detail pages (one per floor plan) ───────────────────────────
    #
    # Each floor plan detail page embeds ALL available units in its __NEXT_DATA__
    # under floorPlan.units[], each with its own price, date, and floor number.
    # We read the full array so every unit gets its actual price and availability.
    #
    log.info("[Phase 2] Fetching detail pages for per-unit prices (1 request per floor plan)...")
    all_units: list[dict] = []
    http_requests = 1  # already fetched main page

    for fp in floorplans:
        unit_ids: list[str] = fp.get("available_unit_ids") or []
        log.info(
            "  %s — %d unit(s) expected",
            fp["name"], len(unit_ids),
        )

        if not unit_ids:
            log.warning("    No unit IDs for %s — skipping", fp["name"])
            continue

        time.sleep(random.uniform(1.5, 3.0))

        floor_param = f"?floor={fp['floor']}" if fp.get("floor") else ""
        detail_url = f"{BASE_URL}/{fp['slug']}{floor_param}"

        try:
            detail_html = fetch(session, detail_url)
            http_requests += 1
            save_snapshot(detail_html, fp["slug"], ts)

            units_from_detail = parse_all_units_from_detail(detail_html, fp)
            if units_from_detail:
                avail_note = build_avail_note(len(units_from_detail))
                for u in units_from_detail:
                    u["avail_note"] = avail_note
                all_units.extend(units_from_detail)
                prices = sorted(set(u["price"] for u in units_from_detail))
                log.info(
                    "    Recorded %d units — prices $%s–$%s (individual per unit)",
                    len(units_from_detail),
                    f"{prices[0]:,}", f"{prices[-1]:,}",
                )
                continue  # skip fallback

            log.warning("    No units parsed from detail page for %s — falling back", fp["name"])

        except RuntimeError as exc:
            log.warning("    Detail page fetch failed for %s: %s — falling back", fp["name"], exc)

        # Fallback: use floor plan starting price for all known unit IDs
        avail_note = build_avail_note(len(unit_ids))
        for uid in unit_ids:
            all_units.append({
                "floorplan_name": fp["name"],
                "floorplan_slug": fp["slug"],
                "unit_id": uid,
                "floor": fp.get("floor"),
                "bedrooms": fp["beds"],
                "bathrooms": fp["baths"],
                "sqft": fp["sqft"],
                "price": fp["starting_price"],
                "available_date": fp.get("available_date"),
                "avail_note": avail_note,
                "special_tags": fp.get("special_tags"),
                "unit_features": None,
            })
        log.info(
            "    Fallback: recorded %d units @ $%s (floor plan starting price)",
            len(unit_ids), f"{fp['starting_price']:,}",
        )

    # ── Insert all units ──────────────────────────────────────────────────────
    for unit in all_units:
        insert_snapshot(conn, unit, ts)
    conn.commit()
    conn.close()

    # ── Export CSVs ───────────────────────────────────────────────────────────
    export_csvs(conn_read := sqlite3.connect(str(DB_PATH)), ts)
    conn_read.close()

    log.info("═" * 55)
    log.info(
        "Done. %d units across %d floor plans  (%d HTTP requests)",
        len(all_units), len(floorplans), http_requests,
    )
    log.info("Database:  %s", DB_PATH)
    log.info("Latest:    %s", ROOT / "data" / "latest.csv")
    log.info("History:   %s", ROOT / "data" / "history.csv")
    log.info("═" * 55)


if __name__ == "__main__":
    main()

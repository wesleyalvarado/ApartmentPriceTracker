"""
Apartment Price Tracker — FastAPI backend.

Reads from data/camden_prices.db (SQLite, written by the scraper).
Serves JSON to the Angular frontend on localhost:4200.

Usage:
    cd api
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Endpoints:
    GET /api/complexes            — list all tracked complexes
    GET /api/floorplans           — summary per floor plan (latest scrape)
    GET /api/latest               — every unit's latest price, filterable
    GET /api/units/{floorplan}    — all units for one floor plan (latest)
    GET /api/history/{unit_id}    — price history for a specific unit
    GET /api/history/floorplan/{floorplan} — min/max history for a floor plan
    GET /api/stats                — min/max/avg/count per floor plan
    GET /api/scrapes              — list of all scrape timestamps
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent.parent / "data" / "camden_prices.db"

app = FastAPI(
    title="Apartment Price Tracker API",
    description="Multi-complex apartment price tracker.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── DB helpers ────────────────────────────────────────────────────────────────

@contextmanager
def get_db():
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Database not found at {DB_PATH}. Run the scraper first.",
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


def latest_ts(conn: sqlite3.Connection, complex_id: Optional[int] = None) -> str:
    if complex_id:
        row = conn.execute(
            "SELECT MAX(scraped_at) AS ts FROM price_snapshots WHERE complex_id = ?",
            (complex_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT MAX(scraped_at) AS ts FROM price_snapshots"
        ).fetchone()
    if not row or not row["ts"]:
        raise HTTPException(status_code=404, detail="No scrape data found.")
    return row["ts"]


def _latest_lease_term_ts(
    conn: sqlite3.Connection,
    lease_months: int,
    complex_id: Optional[int] = None,
) -> str | None:
    if complex_id:
        row = conn.execute(
            "SELECT MAX(scraped_at) FROM lease_term_prices "
            "WHERE lease_months = ? AND complex_id = ?",
            (lease_months, complex_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT MAX(scraped_at) FROM lease_term_prices WHERE lease_months = ?",
            (lease_months,),
        ).fetchone()
    return row[0] if row and row[0] else None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/complexes")
def list_complexes():
    """List all tracked apartment complexes."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, name, display_name, city, state, url
            FROM complexes
            ORDER BY id
            """
        ).fetchall()
    return rows_to_list(rows)


@app.get("/api/scrapes")
def list_scrapes(
    complex_id: Optional[int] = Query(None, description="Filter by complex ID"),
):
    """All scrape timestamps, newest first."""
    with get_db() as conn:
        if complex_id:
            rows = conn.execute(
                """
                SELECT scraped_at, COUNT(*) as unit_count
                FROM price_snapshots
                WHERE complex_id = ?
                GROUP BY scraped_at
                ORDER BY scraped_at DESC
                """,
                (complex_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT scraped_at, COUNT(*) as unit_count
                FROM price_snapshots
                GROUP BY scraped_at
                ORDER BY scraped_at DESC
                """
            ).fetchall()
    return rows_to_list(rows)


@app.get("/api/floorplans")
def get_floorplans(
    complex_id: Optional[int] = Query(None, description="Filter by complex ID. Omit for all complexes."),
    lease_term: Optional[int] = Query(None, description="Lease term months (4/5/6/14). Omit for 15-month default."),
):
    """
    One entry per floor plan showing the latest prices.
    Pass complex_id to filter to one complex; omit for all complexes combined.
    Pass lease_term=4/5/6/14 to get short-term pricing; omit for default 15-month.
    """
    with get_db() as conn:
        if lease_term and lease_term != 15:
            lt_ts = _latest_lease_term_ts(conn, lease_term, complex_id)
            if not lt_ts:
                raise HTTPException(
                    status_code=404,
                    detail=f"No lease term data for {lease_term} months. Run lease_terms.py first.",
                )
            # Use CTE to get per-complex latest snapshot for metadata
            complex_filter = "AND ltp.complex_id = :cid" if complex_id else ""
            rows = conn.execute(
                f"""
                WITH latest_snap AS (
                    SELECT complex_id, MAX(scraped_at) AS ts
                    FROM price_snapshots
                    GROUP BY complex_id
                )
                SELECT
                    ltp.complex_id,
                    c.display_name  AS complex_name,
                    ltp.floorplan_name,
                    ps.floorplan_slug,
                    ps.bedrooms,
                    ps.bathrooms,
                    ps.sqft,
                    COUNT(DISTINCT ltp.unit_id)  AS available_units,
                    MIN(ltp.monthly_rent)         AS min_price,
                    MAX(ltp.monthly_rent)         AS max_price,
                    ROUND(AVG(ltp.monthly_rent))  AS avg_price,
                    MIN(ltp.move_in_date)         AS earliest_available,
                    ps.special_tags,
                    ltp.scraped_at
                FROM lease_term_prices ltp
                JOIN complexes c ON c.id = ltp.complex_id
                JOIN (
                    SELECT ps2.complex_id, ps2.floorplan_name, ps2.floorplan_slug,
                           ps2.bedrooms, ps2.bathrooms, ps2.sqft, ps2.special_tags
                    FROM price_snapshots ps2
                    JOIN latest_snap ls ON ls.complex_id = ps2.complex_id AND ls.ts = ps2.scraped_at
                    GROUP BY ps2.complex_id, ps2.floorplan_name
                ) ps ON ps.complex_id = ltp.complex_id AND ps.floorplan_name = ltp.floorplan_name
                WHERE ltp.scraped_at = :lt_ts AND ltp.lease_months = :term
                  {complex_filter}
                GROUP BY ltp.complex_id, ltp.floorplan_name
                ORDER BY ltp.complex_id, min_price ASC
                """,
                {"lt_ts": lt_ts, "term": lease_term, "cid": complex_id},
            ).fetchall()
        else:
            complex_filter = "AND ps.complex_id = :cid" if complex_id else ""
            rows = conn.execute(
                f"""
                WITH latest AS (
                    SELECT complex_id, MAX(scraped_at) AS ts
                    FROM price_snapshots
                    GROUP BY complex_id
                )
                SELECT
                    ps.complex_id,
                    c.display_name             AS complex_name,
                    ps.floorplan_name,
                    ps.floorplan_slug,
                    ps.bedrooms,
                    ps.bathrooms,
                    ps.sqft,
                    COUNT(DISTINCT ps.unit_id) AS available_units,
                    MIN(ps.price)              AS min_price,
                    MAX(ps.price)              AS max_price,
                    ROUND(AVG(ps.price))       AS avg_price,
                    MIN(ps.available_date)     AS earliest_available,
                    ps.special_tags,
                    l.ts                       AS scraped_at
                FROM price_snapshots ps
                JOIN latest l ON l.complex_id = ps.complex_id AND l.ts = ps.scraped_at
                JOIN complexes c ON c.id = ps.complex_id
                WHERE 1=1 {complex_filter}
                GROUP BY ps.complex_id, ps.floorplan_name
                ORDER BY ps.complex_id, min_price ASC
                """,
                {"cid": complex_id},
            ).fetchall()
    return rows_to_list(rows)


@app.get("/api/latest")
def get_latest(
    complex_id: Optional[int] = Query(None, description="Filter by complex ID"),
    bedrooms: Optional[float] = Query(None, description="Filter by bedroom count (0=studio)"),
    max_price: Optional[int] = Query(None, description="Filter by max price"),
):
    """
    Latest price for every available unit, optionally filtered.
    Returns units sorted cheapest first.
    """
    with get_db() as conn:
        ts = latest_ts(conn, complex_id)

        where_clauses = ["ps.scraped_at = :ts"]
        params: dict = {"ts": ts}

        if complex_id is not None:
            where_clauses.append("ps.complex_id = :cid")
            params["cid"] = complex_id
        if bedrooms is not None:
            where_clauses.append("ps.bedrooms = :br")
            params["br"] = bedrooms
        if max_price is not None:
            where_clauses.append("ps.price <= :mp")
            params["mp"] = max_price

        where = " AND ".join(where_clauses)
        rows = conn.execute(
            f"""
            SELECT
                ps.complex_id,
                c.display_name AS complex_name,
                ps.floorplan_name, ps.floorplan_slug, ps.unit_id, ps.floor,
                ps.bedrooms, ps.bathrooms, ps.sqft, ps.price,
                ps.available_date, ps.avail_note, ps.special_tags, ps.scraped_at
            FROM price_snapshots ps
            JOIN complexes c ON c.id = ps.complex_id
            WHERE {where}
            ORDER BY ps.price ASC, ps.floorplan_name, ps.unit_id
            """,
            params,
        ).fetchall()
    return rows_to_list(rows)


@app.get("/api/units/{floorplan_name}")
def get_units_for_floorplan(
    floorplan_name: str,
    complex_id: Optional[int] = Query(None, description="Filter by complex ID"),
    lease_term: Optional[int] = Query(None, description="Lease term months (4/5/6/14). Omit for default."),
):
    """
    All available units for a specific floor plan, cheapest first.
    Pass complex_id to disambiguate if multiple complexes share a floor plan name.
    Pass lease_term=4/5/6/14 for short-term pricing.
    """
    with get_db() as conn:
        complex_filter = "AND ltp.complex_id = :cid" if complex_id else ""
        snap_complex_filter = "AND ps2.complex_id = :cid" if complex_id else ""

        if lease_term and lease_term != 15:
            lt_ts = _latest_lease_term_ts(conn, lease_term, complex_id)
            if not lt_ts:
                raise HTTPException(
                    status_code=404,
                    detail=f"No lease term data for {lease_term} months. Run lease_terms.py first.",
                )
            rows = conn.execute(
                f"""
                SELECT
                    ltp.complex_id,
                    c.display_name AS complex_name,
                    ltp.unit_id,
                    ps.floor,
                    ps.bedrooms,
                    ps.bathrooms,
                    ps.sqft,
                    ltp.monthly_rent   AS price,
                    ltp.move_in_date   AS available_date,
                    ps.avail_note,
                    ps.special_tags,
                    ps.unit_features,
                    ltp.scraped_at
                FROM lease_term_prices ltp
                JOIN complexes c ON c.id = ltp.complex_id
                JOIN (
                    SELECT ps2.complex_id, ps2.unit_id, ps2.floor, ps2.bedrooms,
                           ps2.bathrooms, ps2.sqft, ps2.avail_note,
                           ps2.special_tags, ps2.unit_features
                    FROM price_snapshots ps2
                    WHERE ps2.scraped_at = (
                              SELECT MAX(scraped_at) FROM price_snapshots
                              WHERE floorplan_name = :fp {snap_complex_filter}
                          )
                      AND ps2.floorplan_name = :fp
                    {snap_complex_filter}
                ) ps ON ps.complex_id = ltp.complex_id AND ps.unit_id = ltp.unit_id
                WHERE ltp.scraped_at = :lt_ts
                  AND ltp.floorplan_name = :fp
                  AND ltp.lease_months = :term
                  {complex_filter}
                ORDER BY ltp.monthly_rent ASC
                """,
                {"fp": floorplan_name, "lt_ts": lt_ts, "term": lease_term, "cid": complex_id},
            ).fetchall()
        else:
            ts = latest_ts(conn, complex_id)
            complex_filter2 = "AND complex_id = :cid" if complex_id else ""
            rows = conn.execute(
                f"""
                SELECT
                    ps.complex_id,
                    c.display_name AS complex_name,
                    ps.unit_id, ps.floor, ps.bedrooms, ps.bathrooms, ps.sqft,
                    ps.price, ps.available_date, ps.avail_note,
                    ps.special_tags, ps.unit_features, ps.scraped_at
                FROM price_snapshots ps
                JOIN complexes c ON c.id = ps.complex_id
                WHERE ps.scraped_at = :ts
                  AND ps.floorplan_name = :fp
                  {complex_filter2}
                ORDER BY ps.price ASC
                """,
                {"ts": ts, "fp": floorplan_name, "cid": complex_id},
            ).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Floor plan '{floorplan_name}' not found.",
        )
    return rows_to_list(rows)


@app.get("/api/history/{unit_id}")
def get_unit_history(
    unit_id: str,
    complex_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
):
    """Price history for a specific unit over the last N days."""
    with get_db() as conn:
        complex_filter = "AND complex_id = ?" if complex_id else ""
        params: list = [unit_id, f"-{days}"]
        if complex_id:
            params.append(complex_id)
        rows = conn.execute(
            f"""
            SELECT scraped_at, price, available_date
            FROM price_snapshots
            WHERE unit_id = ?
              AND scraped_at >= datetime('now', ? || ' days')
              {complex_filter}
            ORDER BY scraped_at ASC
            """,
            params,
        ).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for unit '{unit_id}'.",
        )
    return rows_to_list(rows)


@app.get("/api/history/floorplan/{floorplan_name}")
def get_floorplan_history(
    floorplan_name: str,
    complex_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365),
):
    """
    Price history for a floor plan — min/max/avg across all its units
    at each scrape timestamp. Good for charting trends.
    """
    with get_db() as conn:
        complex_filter = "AND complex_id = ?" if complex_id else ""
        params: list = [floorplan_name, f"-{days}"]
        if complex_id:
            params.append(complex_id)
        rows = conn.execute(
            f"""
            SELECT
                scraped_at,
                MIN(price)        AS min_price,
                MAX(price)        AS max_price,
                ROUND(AVG(price)) AS avg_price,
                COUNT(unit_id)    AS unit_count
            FROM price_snapshots
            WHERE floorplan_name = ?
              AND scraped_at >= datetime('now', ? || ' days')
              {complex_filter}
            GROUP BY scraped_at
            ORDER BY scraped_at ASC
            """,
            params,
        ).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for floor plan '{floorplan_name}'.",
        )
    return rows_to_list(rows)


@app.get("/api/stats")
def get_stats(
    complex_id: Optional[int] = Query(None, description="Filter by complex ID"),
):
    """
    Aggregate stats per floor plan across all scrapes:
    all-time min, all-time max, and latest price.
    """
    with get_db() as conn:
        ts = latest_ts(conn, complex_id)
        complex_filter = "AND p.complex_id = :cid" if complex_id else ""
        rows = conn.execute(
            f"""
            SELECT
                p.complex_id,
                c.display_name          AS complex_name,
                p.floorplan_name,
                p.bedrooms,
                p.bathrooms,
                p.sqft,
                MIN(p.price)            AS all_time_min,
                MAX(p.price)            AS all_time_max,
                (
                    SELECT MIN(p2.price) FROM price_snapshots p2
                    WHERE p2.floorplan_name = p.floorplan_name
                      AND p2.complex_id = p.complex_id
                      AND p2.scraped_at = :ts
                )                       AS current_min,
                COUNT(DISTINCT p.scraped_at)  AS scrape_count,
                COUNT(DISTINCT p.unit_id)     AS total_units_seen
            FROM price_snapshots p
            JOIN complexes c ON c.id = p.complex_id
            WHERE 1=1 {complex_filter}
            GROUP BY p.complex_id, p.floorplan_name
            ORDER BY current_min ASC
            """,
            {"ts": ts, "cid": complex_id},
        ).fetchall()
    return rows_to_list(rows)


@app.get("/api/alerts")
def get_alerts(
    max_price: int = Query(..., description="Alert threshold — show units at or below this price"),
    complex_id: Optional[int] = Query(None),
    bedrooms: Optional[float] = Query(None),
):
    """Return units from the latest scrape whose price is at or below max_price."""
    with get_db() as conn:
        ts = latest_ts(conn, complex_id)

        where_clauses = ["scraped_at = ?", "price <= ?"]
        params: list = [ts, max_price]

        if complex_id is not None:
            where_clauses.append("complex_id = ?")
            params.append(complex_id)
        if bedrooms is not None:
            where_clauses.append("bedrooms = ?")
            params.append(bedrooms)

        where = " AND ".join(where_clauses)
        rows = conn.execute(
            f"""
            SELECT
                complex_id, floorplan_name, unit_id, floor, bedrooms, bathrooms,
                sqft, price, available_date, avail_note, special_tags
            FROM price_snapshots
            WHERE {where}
            ORDER BY price ASC
            """,
            params,
        ).fetchall()
    return {"threshold": max_price, "matches": rows_to_list(rows)}


@app.get("/health")
def health():
    """Quick liveness check."""
    db_ok = DB_PATH.exists()
    return {
        "status": "ok" if db_ok else "db_missing",
        "db": str(DB_PATH),
        "db_exists": db_ok,
        "time": datetime.now(timezone.utc).isoformat(),
    }

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

DB_PATH = Path(__file__).parent.parent / "data" / "apartments.db"

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
            # Verify at least one complex has this lease term
            check_filter = "AND complex_id = ?" if complex_id else ""
            check_params = (lease_term, complex_id) if complex_id else (lease_term,)
            exists = conn.execute(
                f"SELECT 1 FROM lease_term_prices WHERE lease_months=? {check_filter} LIMIT 1",
                check_params,
            ).fetchone()
            if not exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"No lease term data for {lease_term} months. Run lease_terms.py first.",
                )
            cte_complex_filter = "AND complex_id = :cid" if complex_id else ""
            complex_filter = "AND ltp.complex_id = :cid" if complex_id else ""
            rows = conn.execute(
                f"""
                WITH latest_snap AS (
                    SELECT complex_id, MAX(scraped_at) AS ts
                    FROM price_snapshots
                    GROUP BY complex_id
                ),
                current_units AS (
                    SELECT ps2.complex_id, ps2.unit_id, ps2.floorplan_name,
                           ps2.floorplan_slug, ps2.bedrooms, ps2.bathrooms,
                           ps2.sqft, ps2.special_tags, ps2.available_date
                    FROM price_snapshots ps2
                    JOIN latest_snap ls ON ls.complex_id = ps2.complex_id AND ls.ts = ps2.scraped_at
                ),
                latest_lt AS (
                    SELECT complex_id, unit_id, floorplan_name, lease_months,
                           monthly_rent, move_in_date, MAX(scraped_at) AS scraped_at
                    FROM lease_term_prices
                    WHERE lease_months = :term
                      {cte_complex_filter}
                    GROUP BY complex_id, unit_id, lease_months
                )
                SELECT
                    ltp.complex_id,
                    c.display_name               AS complex_name,
                    ltp.floorplan_name,
                    MIN(cu.floorplan_slug)        AS floorplan_slug,
                    MIN(cu.bedrooms)              AS bedrooms,
                    MIN(cu.bathrooms)             AS bathrooms,
                    MIN(cu.sqft)                  AS sqft,
                    COUNT(DISTINCT ltp.unit_id)   AS available_units,
                    MIN(ltp.monthly_rent)          AS min_price,
                    MAX(ltp.monthly_rent)          AS max_price,
                    ROUND(AVG(ltp.monthly_rent))   AS avg_price,
                    (
                        SELECT COALESCE(NULLIF(ltp3.move_in_date, ''), cu3.available_date)
                        FROM latest_lt ltp3
                        JOIN current_units cu3
                          ON cu3.complex_id = ltp3.complex_id AND cu3.unit_id = ltp3.unit_id
                        WHERE ltp3.complex_id = ltp.complex_id
                          AND ltp3.floorplan_name = ltp.floorplan_name
                        ORDER BY ltp3.monthly_rent ASC
                        LIMIT 1
                    )                              AS earliest_available,
                    MIN(cu.special_tags)           AS special_tags,
                    MAX(ltp.scraped_at)            AS scraped_at,
                    fm.image_url,
                    fm.floor                       AS url_floor
                FROM latest_lt ltp
                JOIN current_units cu ON cu.complex_id = ltp.complex_id AND cu.unit_id = ltp.unit_id
                JOIN complexes c ON c.id = ltp.complex_id
                LEFT JOIN floorplan_meta fm ON fm.complex_id = ltp.complex_id AND fm.floorplan_name = ltp.floorplan_name
                WHERE 1=1
                  {complex_filter}
                GROUP BY ltp.complex_id, ltp.floorplan_name
                ORDER BY ltp.complex_id, min_price ASC
                """,
                {"term": lease_term, "cid": complex_id},
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
                    (
                        SELECT ps2.available_date
                        FROM price_snapshots ps2
                        JOIN latest l2
                          ON l2.complex_id = ps2.complex_id AND l2.ts = ps2.scraped_at
                        WHERE ps2.complex_id = ps.complex_id
                          AND ps2.floorplan_name = ps.floorplan_name
                        ORDER BY ps2.price ASC
                        LIMIT 1
                    )                          AS earliest_available,
                    ps.special_tags,
                    l.ts                       AS scraped_at,
                    fm.image_url,
                    fm.floor               AS url_floor
                FROM price_snapshots ps
                JOIN latest l ON l.complex_id = ps.complex_id AND l.ts = ps.scraped_at
                JOIN complexes c ON c.id = ps.complex_id
                LEFT JOIN floorplan_meta fm ON fm.complex_id = ps.complex_id AND fm.floorplan_name = ps.floorplan_name
                WHERE 1=1 {complex_filter}
                  AND (
                    NOT EXISTS (SELECT 1 FROM lease_term_prices ltp2 WHERE ltp2.complex_id = ps.complex_id)
                    OR EXISTS (SELECT 1 FROM lease_term_prices ltp2 WHERE ltp2.complex_id = ps.complex_id AND ltp2.lease_months >= 12)
                  )
                GROUP BY ps.complex_id, ps.floorplan_name
                ORDER BY ps.complex_id, min_price ASC
                """,
                {"cid": complex_id},
            ).fetchall()
    return rows_to_list(rows)


@app.get("/api/lease_terms")
def get_lease_terms(
    complex_id: Optional[int] = Query(None, description="Filter by complex ID"),
):
    """
    Returns the list of available lease term months for a complex (or all complexes).
    Always includes 15 (the default price_snapshots view).
    """
    with get_db() as conn:
        if complex_id:
            rows = conn.execute(
                "SELECT DISTINCT lease_months FROM lease_term_prices "
                "WHERE complex_id = ? ORDER BY lease_months DESC",
                (complex_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT lease_months FROM lease_term_prices ORDER BY lease_months DESC"
            ).fetchall()
    return [r[0] for r in rows]


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
            rows = conn.execute(
                f"""
                WITH latest_snap AS (
                    SELECT complex_id, MAX(scraped_at) AS ts
                    FROM price_snapshots
                    WHERE floorplan_name = :fp
                    GROUP BY complex_id
                ),
                latest_lt AS (
                    SELECT complex_id, unit_id, floorplan_name, lease_months,
                           monthly_rent, move_in_date, MAX(scraped_at) AS scraped_at
                    FROM lease_term_prices
                    WHERE lease_months = :term AND floorplan_name = :fp
                    GROUP BY complex_id, unit_id, lease_months
                )
                SELECT
                    ltp.complex_id,
                    c.display_name AS complex_name,
                    ltp.unit_id,
                    ps.floor,
                    ps.bedrooms,
                    ps.bathrooms,
                    ps.sqft,
                    ltp.monthly_rent   AS price,
                    COALESCE(NULLIF(ltp.move_in_date, ''), ps.available_date) AS available_date,
                    ps.avail_note,
                    ps.special_tags,
                    ps.unit_features,
                    ltp.scraped_at
                FROM latest_lt ltp
                JOIN complexes c ON c.id = ltp.complex_id
                JOIN (
                    SELECT ps2.complex_id, ps2.unit_id, ps2.floor, ps2.bedrooms,
                           ps2.bathrooms, ps2.sqft, ps2.avail_note,
                           ps2.available_date, ps2.special_tags, ps2.unit_features
                    FROM price_snapshots ps2
                    JOIN latest_snap ls ON ls.complex_id = ps2.complex_id AND ls.ts = ps2.scraped_at
                    WHERE ps2.floorplan_name = :fp
                    {snap_complex_filter}
                ) ps ON ps.complex_id = ltp.complex_id AND ps.unit_id = ltp.unit_id
                WHERE 1=1
                  {complex_filter}
                ORDER BY ltp.monthly_rent ASC
                """,
                {"fp": floorplan_name, "term": lease_term, "cid": complex_id},
            ).fetchall()
            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail=f"No lease term data for {lease_term} months. Run lease_terms.py first.",
                )
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


@app.get("/api/rented")
def get_rented(
    complex_id: Optional[int] = Query(None, description="Filter by complex ID"),
    days: int = Query(14, ge=1, le=90, description="Look back N days for rented units"),
):
    """
    Units that appeared in a previous scrape but are absent from the latest scrape.
    Returns each unit with the date it was last seen (i.e., likely rented).
    """
    with get_db() as conn:
        complex_where = "WHERE complex_id = :cid" if complex_id else ""
        rows = conn.execute(
            f"""
            WITH complex_latest AS (
                -- per-complex latest scrape timestamp
                SELECT complex_id, MAX(scraped_at) AS latest_ts
                FROM price_snapshots
                {complex_where}
                GROUP BY complex_id
            ),
            latest_units AS (
                -- units present in each complex's own latest scrape
                SELECT p.unit_id, p.complex_id
                FROM price_snapshots p
                JOIN complex_latest cl
                  ON p.complex_id = cl.complex_id AND p.scraped_at = cl.latest_ts
            )
            SELECT
                p.unit_id,
                p.floorplan_name,
                p.floor,
                p.bedrooms,
                p.price             AS last_price,
                p.available_date    AS last_available_date,
                DATE(MAX(p.scraped_at)) AS last_seen
            FROM price_snapshots p
            JOIN complex_latest cl ON p.complex_id = cl.complex_id
            LEFT JOIN latest_units lu
              ON p.unit_id = lu.unit_id AND p.complex_id = lu.complex_id
            WHERE p.scraped_at >= datetime(cl.latest_ts, :lookback)
              AND p.scraped_at < cl.latest_ts
              AND lu.unit_id IS NULL
            GROUP BY p.unit_id, p.floorplan_name
            ORDER BY p.floorplan_name, p.unit_id
            """,
            {"cid": complex_id, "lookback": f"-{days} days"},
        ).fetchall()
    return rows_to_list(rows)


@app.get("/api/price-drops")
def get_price_drops(
    complex_id: Optional[int] = Query(None, description="Filter by complex ID"),
    lease_term: Optional[int] = Query(None, description="Lease term months. Omit or 15 for standard pricing."),
):
    """
    Per floor plan: the unit with the greatest price drop from its first recorded
    price to the latest scrape. When lease_term is 4/5/6/14, uses lease_term_prices.
    Otherwise uses standard price_snapshots.
    """
    with get_db() as conn:
        if lease_term and lease_term != 15:
            complex_filter = "AND lt.complex_id = :cid" if complex_id else ""
            rows = conn.execute(
                f"""
                WITH current_lt AS (
                    SELECT lt.complex_id, lt.floorplan_name, lt.unit_id,
                           lt.monthly_rent AS current_price
                    FROM lease_term_prices lt
                    WHERE lt.lease_months = :term
                      AND lt.scraped_at = (
                          SELECT MAX(lt2.scraped_at) FROM lease_term_prices lt2
                          WHERE lt2.complex_id = lt.complex_id
                            AND lt2.unit_id = lt.unit_id
                            AND lt2.lease_months = lt.lease_months
                      )
                    {complex_filter}
                ),
                first_lt AS (
                    SELECT lt.complex_id, lt.unit_id,
                           lt.monthly_rent AS first_price,
                           lt.scraped_at   AS first_seen
                    FROM lease_term_prices lt
                    WHERE lt.lease_months = :term
                      AND lt.scraped_at = (
                          SELECT MIN(lt2.scraped_at) FROM lease_term_prices lt2
                          WHERE lt2.complex_id = lt.complex_id
                            AND lt2.unit_id = lt.unit_id
                            AND lt2.lease_months = lt.lease_months
                      )
                ),
                unit_changes AS (
                    SELECT cp.complex_id, cp.floorplan_name, cp.unit_id,
                           cp.current_price, fp.first_price,
                           ABS(fp.first_price - cp.current_price)             AS abs_change,
                           fp.first_price - cp.current_price                  AS price_change,
                           ROUND(ABS(CAST(fp.first_price - cp.current_price AS REAL))
                                 / fp.first_price * 100, 1)                   AS change_pct,
                           CASE WHEN cp.current_price < fp.first_price
                                THEN 'drop' ELSE 'increase' END                AS direction,
                           DATE(fp.first_seen)                                 AS first_seen
                    FROM current_lt cp
                    JOIN first_lt fp
                      ON fp.complex_id = cp.complex_id AND fp.unit_id = cp.unit_id
                    WHERE cp.current_price != fp.first_price
                ),
                ranked AS (
                    SELECT *,
                           ROW_NUMBER() OVER (
                               PARTITION BY complex_id, floorplan_name
                               ORDER BY
                                 CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC,
                                 abs_change DESC
                           ) AS rn
                    FROM unit_changes
                )
                SELECT complex_id, floorplan_name,
                       unit_id       AS best_unit_id,
                       current_price AS current_min,
                       first_price   AS baseline_min,
                       abs_change    AS cumulative_drop,
                       change_pct    AS drop_pct,
                       direction,
                       first_seen
                FROM ranked
                WHERE rn = 1
                ORDER BY
                  CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC,
                  abs_change DESC
                """,
                {"term": lease_term, "cid": complex_id},
            ).fetchall()
        else:
            complex_filter = "AND ps.complex_id = :cid" if complex_id else ""
            rows = conn.execute(
                f"""
                WITH latest_snap AS (
                    SELECT complex_id, MAX(scraped_at) AS ts
                    FROM price_snapshots
                    GROUP BY complex_id
                ),
                current_unit_prices AS (
                    SELECT ps.complex_id, ps.floorplan_name, ps.unit_id, ps.price AS current_price
                    FROM price_snapshots ps
                    JOIN latest_snap ls ON ls.complex_id = ps.complex_id AND ls.ts = ps.scraped_at
                    WHERE 1=1 {complex_filter}
                ),
                first_unit_prices AS (
                    SELECT ps.complex_id, ps.unit_id, ps.price AS first_price,
                           ps.scraped_at AS first_seen
                    FROM price_snapshots ps
                    WHERE ps.scraped_at = (
                        SELECT MIN(scraped_at) FROM price_snapshots ps2
                        WHERE ps2.complex_id = ps.complex_id AND ps2.unit_id = ps.unit_id
                    )
                ),
                unit_changes AS (
                    SELECT cp.complex_id, cp.floorplan_name, cp.unit_id,
                           cp.current_price, fp.first_price,
                           ABS(fp.first_price - cp.current_price)             AS abs_change,
                           fp.first_price - cp.current_price                  AS price_change,
                           ROUND(ABS(CAST(fp.first_price - cp.current_price AS REAL))
                                 / fp.first_price * 100, 1)                   AS change_pct,
                           CASE WHEN cp.current_price < fp.first_price
                                THEN 'drop' ELSE 'increase' END                AS direction,
                           DATE(fp.first_seen)                                 AS first_seen
                    FROM current_unit_prices cp
                    JOIN first_unit_prices fp
                      ON fp.complex_id = cp.complex_id AND fp.unit_id = cp.unit_id
                    WHERE cp.current_price != fp.first_price
                ),
                ranked AS (
                    SELECT *,
                           ROW_NUMBER() OVER (
                               PARTITION BY complex_id, floorplan_name
                               ORDER BY
                                 CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC,
                                 abs_change DESC
                           ) AS rn
                    FROM unit_changes
                )
                SELECT complex_id, floorplan_name,
                       unit_id       AS best_unit_id,
                       current_price AS current_min,
                       first_price   AS baseline_min,
                       abs_change    AS cumulative_drop,
                       change_pct    AS drop_pct,
                       direction,
                       first_seen
                FROM ranked
                WHERE rn = 1
                ORDER BY
                  CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC,
                  abs_change DESC
                """,
                {"cid": complex_id},
            ).fetchall()
    return rows_to_list(rows)


# ── House Price helpers ───────────────────────────────────────────────────────

def _house_tables_exist(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='zhvi_monthly'"
    ).fetchone()
    return row is not None


# ── House Price routes ────────────────────────────────────────────────────────

@app.get("/api/house-prices/summary")
def get_house_price_summary():
    """Latest ZHVI value + Redfin metrics per zip. Returns [] if tables don't exist."""
    with get_db() as conn:
        if not _house_tables_exist(conn):
            return []
        rows = conn.execute(
            """
            SELECT z.zip_code,
                   zn.display_name,
                   zn.neighborhoods,
                   z.median_value    AS zhvi_current,
                   z.month           AS zhvi_month,
                   r.median_list_price,
                   r.median_sale_price,
                   r.inventory,
                   r.days_on_market,
                   r.new_listings,
                   r.period_begin    AS redfin_week
            FROM (
                SELECT zip_code, median_value, month
                FROM zhvi_monthly
                WHERE home_type = 'all_middle_tier'
                  AND (zip_code, month) IN (
                      SELECT zip_code, MAX(month)
                      FROM zhvi_monthly
                      WHERE home_type = 'all_middle_tier'
                      GROUP BY zip_code
                  )
            ) z
            LEFT JOIN (
                SELECT zip_code, median_list_price, median_sale_price,
                       inventory, days_on_market, new_listings, period_begin
                FROM redfin_weekly
                WHERE (zip_code, period_begin) IN (
                    SELECT zip_code, MAX(period_begin)
                    FROM redfin_weekly
                    GROUP BY zip_code
                )
            ) r ON z.zip_code = r.zip_code
            LEFT JOIN zip_neighborhoods zn ON z.zip_code = zn.zip_code
            ORDER BY z.zip_code
            """
        ).fetchall()
    return rows_to_list(rows)


@app.get("/api/house-prices/zhvi")
def get_zhvi(
    zip_code: Optional[str] = Query(None, description="Filter by zip code"),
    home_type: str = Query("all_middle_tier", description="ZHVI home type variant"),
    months: int = Query(24, ge=1, le=300, description="Number of months of history"),
):
    """Monthly ZHVI trend for target zip codes. Returns [] if tables don't exist."""
    with get_db() as conn:
        if not _house_tables_exist(conn):
            return []
        query = (
            "SELECT zip_code, month, median_value, home_type "
            "FROM zhvi_monthly "
            "WHERE home_type = ? "
            "  AND month >= date('now', ?) "
        )
        params: list = [home_type, f"-{months} months"]
        if zip_code:
            query += " AND zip_code = ?"
            params.append(zip_code)
        query += " ORDER BY zip_code, month"
        rows = conn.execute(query, params).fetchall()
    return rows_to_list(rows)


@app.get("/api/house-prices/redfin")
def get_redfin(
    zip_code: Optional[str] = Query(None, description="Filter by zip code"),
    months: int = Query(12, ge=1, le=300, description="Number of months of history"),
):
    """Weekly Redfin market metrics for target zip codes. Returns [] if tables don't exist."""
    with get_db() as conn:
        if not _house_tables_exist(conn):
            return []
        query = (
            "SELECT zip_code, period_begin, period_end, "
            "       median_sale_price, median_list_price, "
            "       homes_sold, new_listings, inventory, "
            "       days_on_market, sale_to_list_ratio, median_ppsf "
            "FROM redfin_weekly "
            "WHERE period_begin >= date('now', ?) "
        )
        params: list = [f"-{months} months"]
        if zip_code:
            query += " AND zip_code = ?"
            params.append(zip_code)
        query += " ORDER BY zip_code, period_begin"
        rows = conn.execute(query, params).fetchall()
    return rows_to_list(rows)


@app.get("/api/house-prices/mortgage-check")
def mortgage_check(
    max_monthly: float = Query(3500, description="Max total monthly payment"),
    rate: float = Query(6.3, description="Annual mortgage rate (%)"),
    down_pct: float = Query(20, description="Down payment percentage"),
    tax_rate: float = Query(2.2, description="Annual property tax rate (%)"),
    insurance_annual: float = Query(2100, description="Annual homeowner's insurance ($)"),
):
    """Calculate max purchase price for a given monthly budget."""
    monthly_insurance = insurance_annual / 12
    r = (rate / 100) / 12
    n = 360
    factor = (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    price_coefficient = (1 - down_pct / 100) * factor + (tax_rate / 100 / 12)
    max_price = (max_monthly - monthly_insurance) / price_coefficient
    return {
        "max_purchase_price":   round(max_price),
        "down_payment_amount":  round(max_price * down_pct / 100),
        "loan_amount":          round(max_price * (1 - down_pct / 100)),
        "monthly_pi":           round(max_price * (1 - down_pct / 100) * factor),
        "monthly_tax":          round(max_price * tax_rate / 100 / 12),
        "monthly_insurance":    round(monthly_insurance),
        "total_monthly":        round(max_monthly),
    }


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

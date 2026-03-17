"""lease_terms.py — Phase 2: per-lease-term pricing via Camden's GraphQL API.

Camden exposes a GraphQL endpoint at https://api.camdenliving.com/graphql that
returns per-unit pricing for any lease term. No browser needed.

Data sources:
  - Main page __NEXT_DATA__ → realPageFloorPlanId per floor plan
  - Detail page __NEXT_DATA__ → realPageUnitId + moveInDate per unit
  - GraphQL API → currentRent for any (unit, moveInDate, leaseTerm) combination

Usage:
    cd scraper
    python lease_terms.py
"""

import json
import logging
import random
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

DESIRED_TERMS   = [4, 5, 6, 14]
COMMUNITY_ID    = 4877024            # Camden Greenville RealPage community ID
COMPLEX_ID      = 1                  # Camden Greenville — see complexes table
ROOT            = Path(__file__).parent.parent
DB_PATH         = ROOT / "data" / "camden_prices.db"
SNAPSHOTS_DIR   = ROOT / "data" / "snapshots"

BASE_URL = (
    "https://www.camdenliving.com"
    "/apartments/dallas-tx/camden-greenville/available-apartments"
)
GRAPHQL_URL = "https://api.camdenliving.com/graphql"

GQL_QUERY = """
query ($communityId: Int!, $floorPlanId: Int!, $unitId: Int!,
       $moveInDate: String!, $leaseTerm: Int!) {
  getCustomQuoteData(
    communityId: $communityId
    floorPlanId: $floorPlanId
    unitId: $unitId
    moveInDate: $moveInDate
    leaseTerm: $leaseTerm
  ) {
    currentRent
    leaseTerms { leaseTerm }
    nextDates { moveInDate leaseTerm monthlyRent }
  }
}
""".strip()

USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
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


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Accept":           "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language":  "en-US,en;q=0.9",
        "Accept-Encoding":  "gzip, deflate, br",
        "Connection":       "keep-alive",
    })
    return s


def _fetch_html(session: requests.Session, url: str) -> str:
    session.headers["User-Agent"] = random.choice(USER_AGENTS)
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def _query_graphql(
    session: requests.Session,
    floor_plan_id: int,
    unit_id: int,
    move_in_date: str,
    lease_term: int,
) -> int | None:
    """
    Call Camden's GraphQL API and return the monthly rent for the given
    (unit, moveInDate, leaseTerm) combination.  Returns None on failure.
    """
    payload = {
        "query": GQL_QUERY,
        "variables": {
            "communityId": COMMUNITY_ID,
            "floorPlanId": floor_plan_id,
            "unitId":      unit_id,
            "moveInDate":  move_in_date,
            "leaseTerm":   lease_term,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent":   random.choice(USER_AGENTS),
        "Referer":      "https://www.camdenliving.com/",
        "Origin":       "https://www.camdenliving.com",
    }
    try:
        resp = session.post(GRAPHQL_URL, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        rent = data["data"]["getCustomQuoteData"]["currentRent"]
        return int(rent) if rent else None
    except Exception as exc:
        log.warning("    GraphQL failed (fp=%d unit=%d term=%d): %s",
                    floor_plan_id, unit_id, lease_term, exc)
        return None


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _extract_next_data(html: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    tag  = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        return json.loads(tag.string)
    except (json.JSONDecodeError, ValueError):
        return None


def _get_floor_plan_id(main_nd: dict, fp_name: str) -> int | None:
    """Return realPageFloorPlanId for a floor plan from main-page __NEXT_DATA__."""
    try:
        apts = main_nd["props"]["pageProps"]["data"]["availableApartments"]
        for ap in apts:
            if ap.get("name") == fp_name:
                return ap.get("realPageFloorPlanId")
    except (KeyError, TypeError):
        pass
    return None


def _get_units_from_detail(detail_html: str) -> list[dict]:
    """
    Parse detail page __NEXT_DATA__ to get per-unit data including
    realPage unitId (integer), unitName (4-digit string), and moveInDate.
    """
    nd = _extract_next_data(detail_html)
    if not nd:
        return []
    try:
        units = nd["props"]["pageProps"]["data"]["floorPlan"]["units"]
    except (KeyError, TypeError):
        return []

    results = []
    for u in units:
        rp_unit_id = u.get("unitId")          # integer, used in GraphQL
        unit_name  = str(u.get("unitName") or "")
        move_in    = (u.get("moveInDate") or "")[:10]
        price_15mo = int(u.get("monthlyRent") or 0)

        if not rp_unit_id or not unit_name or not move_in:
            continue
        results.append({
            "rp_unit_id":  int(rp_unit_id),
            "unit_name":   unit_name,
            "move_in":     move_in,
            "price_15mo":  price_15mo,
        })
    return results


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_floor_plans_from_db(conn: sqlite3.Connection) -> list[dict]:
    """Return floor plans with their URL floor param from floorplan_meta."""
    rows = conn.execute(
        """
        SELECT floorplan_name, floorplan_slug, floor
        FROM floorplan_meta
        WHERE complex_id = ?
        ORDER BY floorplan_name
        """,
        (COMPLEX_ID,),
    ).fetchall()
    return [dict(r) for r in rows]


def insert_lease_term_price(conn: sqlite3.Connection, rec: dict) -> None:
    conn.execute(
        """
        INSERT INTO lease_term_prices
            (scraped_at, complex_id, unit_id, floorplan_name, move_in_date,
             lease_months, monthly_rent, total_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rec["scraped_at"],
            rec.get("complex_id", COMPLEX_ID),
            rec["unit_id"],
            rec["floorplan_name"],
            rec.get("move_in_date") or "",
            rec["lease_months"],
            rec["monthly_rent"],
            rec.get("total_cost"),
        ),
    )


def save_snapshot(html: str, name: str, ts: str) -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_ts = ts.replace(":", "-").replace(".", "-")
    path = SNAPSHOTS_DIR / f"{safe_ts}_{name}.html"
    path.write_text(html, encoding="utf-8")


# ── Main logic ────────────────────────────────────────────────────────────────

def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log.info("═" * 55)
    log.info("Camden lease-term pricing  %s", ts)
    log.info("Desired terms: %s months", DESIRED_TERMS)
    log.info("═" * 55)

    if not DB_PATH.exists():
        log.error("DB not found at %s — run scraper.py first", DB_PATH)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    floor_plans = get_floor_plans_from_db(conn)
    if not floor_plans:
        log.error("No floor plans in DB — run scraper.py first")
        conn.close()
        sys.exit(1)

    session = _make_session()

    # ── Phase 1: fetch main page for realPageFloorPlanId mapping ─────────────
    log.info("[Phase 1] Fetching main listing page for floor plan IDs...")
    try:
        main_html = _fetch_html(session, BASE_URL)
    except Exception as exc:
        log.error("Could not fetch main page: %s", exc)
        conn.close()
        sys.exit(1)

    main_nd = _extract_next_data(main_html)
    if not main_nd:
        log.error("No __NEXT_DATA__ on main page")
        conn.close()
        sys.exit(1)

    # Build name → realPageFloorPlanId map
    fp_id_map: dict[str, int] = {}
    try:
        apts = main_nd["props"]["pageProps"]["data"]["availableApartments"]
        for ap in apts:
            name   = ap.get("name")
            rp_id  = ap.get("realPageFloorPlanId")
            if name and rp_id:
                fp_id_map[name] = int(rp_id)
    except (KeyError, TypeError):
        pass

    log.info("  Found floor plan IDs: %s", fp_id_map)

    # ── Phase 2: per-floor-plan detail pages + GraphQL pricing ───────────────
    log.info("[Phase 2] Fetching detail pages and querying GraphQL per unit...")
    all_records: list[dict] = []

    for i, fp in enumerate(floor_plans, 1):
        name = fp["floorplan_name"]
        slug = fp["floorplan_slug"]
        rp_fp_id = fp_id_map.get(name)

        if not rp_fp_id:
            log.warning("[%d/%d] %s — no realPageFloorPlanId, skipping",
                        i, len(floor_plans), name)
            continue

        log.info("[%d/%d] %s  (floorPlanId=%d)",
                 i, len(floor_plans), name, rp_fp_id)

        # Fetch detail page to get per-unit realPage IDs
        # ?floor=N is required — server returns no floorPlan.units without it
        time.sleep(random.uniform(1.5, 2.5))
        floor_param = f"?floor={fp['floor']}" if fp.get("floor") else ""
        detail_url = f"{BASE_URL}/{slug}{floor_param}"
        try:
            detail_html = _fetch_html(session, detail_url)
            save_snapshot(detail_html, f"lease_{slug}", ts)
        except Exception as exc:
            log.warning("  Detail page fetch failed: %s", exc)
            continue

        units = _get_units_from_detail(detail_html)
        if not units:
            log.warning("  No units parsed from detail page")
            continue

        log.info("  %d units found", len(units))

        # For each unit, query GraphQL for each desired lease term
        fp_records: list[dict] = []

        for u in units:
            for term in DESIRED_TERMS:
                time.sleep(random.uniform(0.3, 0.7))  # gentle rate limiting

                rent = _query_graphql(
                    session,
                    floor_plan_id=rp_fp_id,
                    unit_id=u["rp_unit_id"],
                    move_in_date=u["move_in"],
                    lease_term=term,
                )

                if rent is None:
                    # Fallback: estimate from 15-month price using typical premium
                    log.debug("    %s/%d-mo: no GraphQL response, skipping",
                              u["unit_name"], term)
                    continue

                fp_records.append({
                    "scraped_at":     ts,
                    "unit_id":        u["unit_name"],
                    "floorplan_name": name,
                    "move_in_date":   u["move_in"],
                    "lease_months":   term,
                    "monthly_rent":   rent,
                    "total_cost":     rent * term,
                })

            log.info("  unit %s: 15mo=$%s  %s",
                     u["unit_name"],
                     f"{u['price_15mo']:,}",
                     "  ".join(
                         f"{r['lease_months']}mo=${r['monthly_rent']:,}"
                         for r in fp_records
                         if r["unit_id"] == u["unit_name"]
                     ) or "(no data)")

        all_records.extend(fp_records)
        log.info("  → %d records for %s", len(fp_records), name)

    # ── Write to DB ──────────────────────────────────────────────────────────
    if all_records:
        for rec in all_records:
            insert_lease_term_price(conn, rec)
        conn.commit()

        log.info("─" * 55)
        log.info("Wrote %d records to lease_term_prices", len(all_records))

        # Summary by term
        by_term: dict[int, list[int]] = {}
        for r in all_records:
            by_term.setdefault(r["lease_months"], []).append(r["monthly_rent"])
        for term in sorted(by_term):
            prices = by_term[term]
            log.info("  %2d-month: %d units  $%s – $%s",
                     term, len(prices),
                     f"{min(prices):,}", f"{max(prices):,}")
    else:
        log.warning("No records captured")

    conn.close()
    log.info("═" * 55)
    log.info("Done. DB: %s", DB_PATH)
    log.info("═" * 55)


if __name__ == "__main__":
    main()

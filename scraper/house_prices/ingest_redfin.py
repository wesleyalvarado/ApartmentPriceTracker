"""
ingest_redfin.py — Download and ingest Redfin weekly market data for target zip codes.

Usage:
    python scraper/house_prices/ingest_redfin.py

Run weekly (Sundays or Mondays) or on-demand.
Warning: The full Redfin file is ~500MB compressed. The script streams
and filters to target zips only.
"""

import csv
import gzip
import io
import sqlite3
from pathlib import Path
from urllib.request import urlopen

from migrate import create_tables

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "apartments.db"
TARGET_ZIPS = {"75206", "75214", "75238"}

REDFIN_URL = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz"


def safe_float(val: str | None) -> float | None:
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


def safe_int(val: str | None) -> int | None:
    try:
        return int(float(val)) if val else None
    except (ValueError, TypeError):
        return None


def ingest() -> None:
    print("Downloading Redfin data (~500MB compressed, may take a few minutes)...")
    resp = urlopen(REDFIN_URL)
    decompressed = gzip.GzipFile(fileobj=io.BytesIO(resp.read()))
    text = decompressed.read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(text), delimiter="\t")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure tables exist before inserting
    create_tables(conn)

    inserted = 0
    for row in reader:
        region = row.get("region", "")
        # Region may be "Zip Code: 75206" or just "75206"
        zip_code = region.replace("Zip Code: ", "").strip()
        if zip_code not in TARGET_ZIPS:
            continue

        cur.execute(
            """
            INSERT OR IGNORE INTO redfin_weekly
                (zip_code, period_begin, period_end, median_sale_price,
                 median_list_price, homes_sold, new_listings, inventory,
                 days_on_market, sale_to_list_ratio, median_ppsf)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                zip_code,
                row.get("period_begin", ""),
                row.get("period_end", ""),
                safe_float(row.get("median_sale_price")),
                safe_float(row.get("median_list_price")),
                safe_int(row.get("homes_sold")),
                safe_int(row.get("new_listings")),
                safe_int(row.get("inventory")),
                safe_float(row.get("days_on_market")),
                safe_float(row.get("avg_sale_to_list")),
                safe_float(row.get("median_ppsf")),
            ),
        )
        inserted += cur.rowcount

    conn.commit()
    conn.close()
    print(f"Ingested {inserted} new weekly rows")


if __name__ == "__main__":
    ingest()

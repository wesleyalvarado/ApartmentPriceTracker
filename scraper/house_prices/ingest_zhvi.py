"""
ingest_zhvi.py — Download and ingest Zillow ZHVI data for target zip codes.

Usage:
    python scraper/house_prices/ingest_zhvi.py
    python scraper/house_prices/ingest_zhvi.py --type 3bed
    python scraper/house_prices/ingest_zhvi.py --all-types

Run monthly (after the 15th) or on-demand.
"""

import csv
import io
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

from migrate import create_tables

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "apartments.db"
TARGET_ZIPS = {"75206", "75214", "75238"}

ZHVI_URLS = {
    "all_middle_tier": "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    "3bed": "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_bdrmcnt_3_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    "sfr_only": "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfr_tier_0.33_0.67_sm_sa_month.csv",
}

META_COLS = {"RegionID", "SizeRank", "RegionName", "RegionType",
             "StateName", "State", "City", "Metro", "CountyName"}


def download_csv(url: str) -> list[dict]:
    """Download CSV from Zillow and return rows for target zips."""
    print(f"Downloading {url} ...")
    resp = urlopen(url)
    text = resp.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader if row.get("RegionName") in TARGET_ZIPS]


def ingest(home_type: str = "all_middle_tier") -> None:
    url = ZHVI_URLS.get(home_type)
    if not url:
        print(f"Unknown type: {home_type}. Options: {list(ZHVI_URLS.keys())}")
        sys.exit(1)

    rows = download_csv(url)
    if not rows:
        print("No matching zip codes found in download.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure tables exist before inserting
    create_tables(conn)

    inserted = 0
    for row in rows:
        zip_code = row["RegionName"]
        for col, val in row.items():
            if col in META_COLS or not val:
                continue
            try:
                datetime.strptime(col, "%Y-%m-%d")
            except ValueError:
                continue
            cur.execute(
                "INSERT OR IGNORE INTO zhvi_monthly (zip_code, month, home_type, median_value) "
                "VALUES (?, ?, ?, ?)",
                (zip_code, col, home_type, float(val)),
            )
            inserted += cur.rowcount

    conn.commit()
    conn.close()
    print(f"Ingested {inserted} new rows for {home_type} ({len(rows)} zips found)")


if __name__ == "__main__":
    if "--all-types" in sys.argv:
        for ht in ZHVI_URLS:
            ingest(ht)
    else:
        home_type = "all_middle_tier"
        if "--type" in sys.argv:
            idx = sys.argv.index("--type")
            if idx + 1 < len(sys.argv):
                home_type = sys.argv[idx + 1]
        ingest(home_type)

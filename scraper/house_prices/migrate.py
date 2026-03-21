"""
migrate.py — Create house price tables in camden_prices.db and seed zip_neighborhoods.

Usage:
    python scraper/house_prices/migrate.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "apartments.db"


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all three house price tables if they don't already exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS zhvi_monthly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zip_code TEXT NOT NULL,
            month TEXT NOT NULL,
            home_type TEXT NOT NULL,
            median_value REAL,
            scraped_at TEXT DEFAULT (datetime('now')),
            UNIQUE(zip_code, month, home_type)
        );

        CREATE TABLE IF NOT EXISTS redfin_weekly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zip_code TEXT NOT NULL,
            period_begin TEXT NOT NULL,
            period_end TEXT NOT NULL,
            median_sale_price REAL,
            median_list_price REAL,
            homes_sold INTEGER,
            new_listings INTEGER,
            inventory INTEGER,
            days_on_market REAL,
            sale_to_list_ratio REAL,
            median_ppsf REAL,
            scraped_at TEXT DEFAULT (datetime('now')),
            UNIQUE(zip_code, period_begin)
        );

        CREATE TABLE IF NOT EXISTS zip_neighborhoods (
            zip_code TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            neighborhoods TEXT,
            notes TEXT
        );
    """)

    conn.execute("""
        INSERT OR IGNORE INTO zip_neighborhoods (zip_code, display_name, neighborhoods, notes)
        VALUES
            ('75206', 'M Streets / Lower Greenville',
             'M Streets, Lower Greenville, Vickery Place, Glencoe Park',
             'Core target zip — Tudor/Craftsman, walkable to Greenville Ave'),
            ('75214', 'Lakewood',
             'Lakewood, Lakewood Heights, Old Lake Highlands',
             'Near White Rock Lake, family-oriented'),
            ('75238', 'Lake Highlands',
             'Lake Highlands, White Rock, Forest Hills',
             'NE Dallas; mix of mid-century ranches and updated homes near White Rock Lake')
    """)
    conn.commit()


def run():
    conn = sqlite3.connect(DB_PATH)
    try:
        create_tables(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    print("Migration complete — tables created and zip_neighborhoods seeded.")

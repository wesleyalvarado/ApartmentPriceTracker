"""migrate_add_complexes.py — One-time migration to add multi-complex support.

Adds a `complexes` table and `complex_id` FK column to all data tables.
Existing Camden Greenville data is tagged as complex_id = 1.

Safe to re-run — all operations are idempotent.

Usage:
    cd scraper
    python migrate_add_complexes.py
"""

import sqlite3
import sys
from pathlib import Path

ROOT    = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "apartments.db"


def migrate(conn: sqlite3.Connection) -> None:
    print("Running multi-complex migration...")

    # ── 1. Create complexes table ─────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS complexes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL UNIQUE,
            display_name TEXT    NOT NULL,
            city         TEXT    NOT NULL,
            state        TEXT    NOT NULL DEFAULT 'TX',
            url          TEXT,
            community_id INTEGER,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # ── 2. Seed Camden Greenville as id = 1 ───────────────────────────────────
    conn.execute("""
        INSERT OR IGNORE INTO complexes
            (id, name, display_name, city, state, url, community_id, created_at)
        VALUES
            (1, 'camden-greenville', 'Camden Greenville', 'Dallas', 'TX',
             'https://www.camdenliving.com/apartments/dallas-tx/camden-greenville',
             4877024, datetime('now'))
    """)
    print("  ✓ complexes table ready — Camden Greenville = id 1")

    # ── 3. Add complex_id to price_snapshots ─────────────────────────────────
    try:
        conn.execute(
            "ALTER TABLE price_snapshots ADD COLUMN complex_id INTEGER NOT NULL DEFAULT 1"
        )
        print("  ✓ price_snapshots.complex_id added")
    except Exception as exc:
        print(f"  ~ price_snapshots.complex_id already exists ({exc})")

    # ── 4. Add complex_id to price_alerts ────────────────────────────────────
    try:
        conn.execute(
            "ALTER TABLE price_alerts ADD COLUMN complex_id INTEGER NOT NULL DEFAULT 1"
        )
        print("  ✓ price_alerts.complex_id added")
    except Exception as exc:
        print(f"  ~ price_alerts.complex_id already exists ({exc})")

    # ── 5. Add complex_id to lease_term_prices ────────────────────────────────
    try:
        conn.execute(
            "ALTER TABLE lease_term_prices ADD COLUMN complex_id INTEGER NOT NULL DEFAULT 1"
        )
        print("  ✓ lease_term_prices.complex_id added")
    except Exception as exc:
        print(f"  ~ lease_term_prices.complex_id already exists ({exc})")

    # ── 6. Recreate floorplan_meta with composite PK (complex_id, floorplan_name) ─
    # The old table had floorplan_name TEXT PRIMARY KEY — fine for one complex,
    # but breaks when a second complex uses the same floor-plan name.
    has_col = conn.execute(
        "SELECT 1 FROM pragma_table_info('floorplan_meta') WHERE name='complex_id'"
    ).fetchone()

    if not has_col:
        conn.execute("""
            CREATE TABLE floorplan_meta_new (
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
            )
        """)
        conn.execute(
            "INSERT INTO floorplan_meta_new SELECT 1, * FROM floorplan_meta"
        )
        conn.execute("DROP TABLE floorplan_meta")
        conn.execute("ALTER TABLE floorplan_meta_new RENAME TO floorplan_meta")
        print("  ✓ floorplan_meta recreated with composite PK (complex_id, floorplan_name)")
    else:
        print("  ~ floorplan_meta.complex_id already exists")

    # ── 7. Performance indexes ────────────────────────────────────────────────
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_complex_id ON price_snapshots(complex_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_lt_complex ON lease_term_prices(complex_id)"
    )
    print("  ✓ indexes created")

    conn.commit()
    print("Migration complete!")


def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}. Run scraper.py first.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        migrate(conn)
    except Exception as exc:
        print(f"ERROR: {exc}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

-- Compare the two most recent price snapshots.
-- Usage: sqlite3 data/apartments.db < queries/snapshot_diff.sql

WITH timestamps AS (
    SELECT DISTINCT scraped_at FROM price_snapshots ORDER BY scraped_at DESC LIMIT 2
),
latest_ts AS (SELECT scraped_at FROM timestamps LIMIT 1),
prev_ts   AS (SELECT scraped_at FROM timestamps LIMIT 1 OFFSET 1),
latest AS (
    SELECT * FROM price_snapshots WHERE scraped_at = (SELECT scraped_at FROM latest_ts)
),
prev AS (
    SELECT * FROM price_snapshots WHERE scraped_at = (SELECT scraped_at FROM prev_ts)
)

SELECT
    'CHANGED'            AS status,
    l.unit_id,
    l.floorplan_name,
    p.price              AS prev_price,
    l.price              AS new_price,
    l.price - p.price    AS delta,
    p.available_date     AS prev_avail,
    l.available_date     AS new_avail
FROM latest l
JOIN prev p ON l.unit_id = p.unit_id
WHERE l.price != p.price OR l.available_date != p.available_date

UNION ALL

SELECT
    'NEW',
    l.unit_id,
    l.floorplan_name,
    NULL, l.price, NULL, NULL, l.available_date
FROM latest l
WHERE l.unit_id NOT IN (SELECT unit_id FROM prev)

UNION ALL

SELECT
    'GONE',
    p.unit_id,
    p.floorplan_name,
    p.price, NULL, NULL, p.available_date, NULL
FROM prev p
WHERE p.unit_id NOT IN (SELECT unit_id FROM latest)

ORDER BY status, floorplan_name, unit_id;

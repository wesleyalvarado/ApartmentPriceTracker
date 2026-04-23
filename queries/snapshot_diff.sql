-- Compare today's snapshot vs the previous day's snapshot.
-- "Today" = most recent row per unit on the latest scrape date.
-- "Prev"  = most recent row per unit on the second-most-recent scrape date.
-- This prevents intra-day partial scrapes from making units appear GONE.
-- Usage: sqlite3 data/apartments.db < queries/snapshot_diff.sql

WITH dates AS (
    SELECT DISTINCT DATE(scraped_at) AS d FROM price_snapshots ORDER BY d DESC LIMIT 2
),
latest_date AS (SELECT d FROM dates LIMIT 1),
prev_date   AS (SELECT d FROM dates LIMIT 1 OFFSET 1),
latest AS (
    SELECT ps.*
    FROM price_snapshots ps
    INNER JOIN (
        SELECT unit_id, MAX(scraped_at) AS best
        FROM price_snapshots
        WHERE DATE(scraped_at) = (SELECT d FROM latest_date)
        GROUP BY unit_id
    ) best ON ps.unit_id = best.unit_id AND ps.scraped_at = best.best
),
prev AS (
    SELECT ps.*
    FROM price_snapshots ps
    INNER JOIN (
        SELECT unit_id, MAX(scraped_at) AS best
        FROM price_snapshots
        WHERE DATE(scraped_at) = (SELECT d FROM prev_date)
        GROUP BY unit_id
    ) best ON ps.unit_id = best.unit_id AND ps.scraped_at = best.best
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

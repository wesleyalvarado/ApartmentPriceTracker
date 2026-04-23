-- Run after daily scrape to check if A2R market conditions changed materially
-- Relevant to: RENEWAL_NEGOTIATION.md — unit #440, targeting 9mo @ $1,799

-- 1. Current A2R market floor vs. yesterday
SELECT
    date(scraped_at) AS scrape_date,
    COUNT(*) AS units_available,
    MIN(price) AS floor_price,
    MAX(price) AS ceiling_price,
    ROUND(AVG(price), 0) AS avg_price
FROM price_snapshots
WHERE floorplan_name = 'A2R Flats'
AND scraped_at >= date('now', '-2 days')
GROUP BY date(scraped_at)
ORDER BY scrape_date DESC;

-- 2. Flag if floor dropped below $1,750 (strengthens negotiation ask)
SELECT
    'ALERT: A2R floor dropped to ' || MIN(price) || ' — update renewal ask' AS negotiation_flag
FROM price_snapshots
WHERE floorplan_name = 'A2R Flats'
AND scraped_at = (SELECT MAX(scraped_at) FROM price_snapshots)
AND price < 1750;

-- 3. Flag if unit count dropped significantly (weakens leverage)
SELECT
    CASE
        WHEN COUNT(*) < 4 THEN 'WARNING: Only ' || COUNT(*) || ' A2R units left — leverage dropping'
        WHEN COUNT(*) >= 8 THEN 'GOOD: ' || COUNT(*) || ' A2R units available — strong leverage'
        ELSE 'NEUTRAL: ' || COUNT(*) || ' A2R units available'
    END AS vacancy_status
FROM price_snapshots
WHERE floorplan_name = 'A2R Flats'
AND scraped_at = (SELECT MAX(scraped_at) FROM price_snapshots);

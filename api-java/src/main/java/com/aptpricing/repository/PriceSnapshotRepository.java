package com.aptpricing.repository;

import com.aptpricing.entity.PriceSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface PriceSnapshotRepository extends JpaRepository<PriceSnapshot, Integer> {

    // ── Projections ───────────────────────────────────────────────────────────

    interface ScrapeProjection {
        String getScrapedAt();
        Long getUnitCount();
    }

    interface LatestUnitProjection {
        Integer getComplexId();
        String getComplexName();
        String getFloorplanName();
        String getFloorplanSlug();
        String getUnitId();
        Integer getFloor();
        Double getBedrooms();
        Double getBathrooms();
        Integer getSqft();
        Integer getPrice();
        String getAvailableDate();
        String getAvailNote();
        String getSpecialTags();
        String getScrapedAt();
    }

    interface FloorplanSummaryProjection {
        Integer getComplexId();
        String getComplexName();
        String getFloorplanName();
        String getFloorplanSlug();
        Double getBedrooms();
        Double getBathrooms();
        Integer getSqft();
        Long getAvailableUnits();
        Integer getMinPrice();
        Integer getMaxPrice();
        Long getAvgPrice();
        String getEarliestAvailable();
        String getSpecialTags();
        String getScrapedAt();
        String getImageUrl();
        Integer getUrlFloor();
    }

    interface UnitProjection {
        Integer getComplexId();
        String getComplexName();
        String getUnitId();
        Integer getFloor();
        Double getBedrooms();
        Double getBathrooms();
        Integer getSqft();
        Integer getPrice();
        String getAvailableDate();
        String getAvailNote();
        String getSpecialTags();
        String getUnitFeatures();
        String getScrapedAt();
    }

    interface StatsProjection {
        Integer getComplexId();
        String getComplexName();
        String getFloorplanName();
        Double getBedrooms();
        Double getBathrooms();
        Integer getSqft();
        Integer getAllTimeMin();
        Integer getAllTimeMax();
        Integer getCurrentMin();
        Long getScrapeCount();
        Long getTotalUnitsSeen();
    }

    interface AlertUnitProjection {
        Integer getComplexId();
        String getFloorplanName();
        String getUnitId();
        Integer getFloor();
        Double getBedrooms();
        Double getBathrooms();
        Integer getSqft();
        Integer getPrice();
        String getAvailableDate();
        String getAvailNote();
        String getSpecialTags();
    }

    interface HistoryProjection {
        String getScrapedAt();
        Integer getMinPrice();
        Integer getMaxPrice();
        Long getAvgPrice();
        Long getUnitCount();
    }

    interface UnitHistoryProjection {
        String getScrapedAt();
        Integer getPrice();
        String getAvailableDate();
    }

    interface RentedUnitProjection {
        String getUnitId();
        String getFloorplanName();
        Integer getFloor();
        Double getBedrooms();
        Integer getLastPrice();
        String getLastAvailableDate();
        String getLastSeen();
    }

    interface PriceDropProjection {
        Integer getComplexId();
        String getFloorplanName();
        String getBestUnitId();
        Integer getCurrentMin();
        Integer getBaselineMin();
        Integer getCumulativeDrop();
        Double getDropPct();
        String getDirection();
        String getFirstSeen();
    }

    // ── Queries ───────────────────────────────────────────────────────────────

    @Query(value = """
            SELECT MAX(scraped_at) FROM price_snapshots
            WHERE (:cid IS NULL OR complex_id = :cid)
            """, nativeQuery = true)
    String findLatestTimestamp(@Param("cid") Integer complexId);

    @Query(value = """
            SELECT scraped_at AS scrapedAt, COUNT(*) AS unitCount
            FROM price_snapshots
            WHERE (:cid IS NULL OR complex_id = :cid)
            GROUP BY scraped_at ORDER BY scraped_at DESC
            """, nativeQuery = true)
    List<ScrapeProjection> findScrapes(@Param("cid") Integer complexId);

    @Query(value = """
            SELECT ps.complex_id AS complexId, c.display_name AS complexName,
              ps.floorplan_name AS floorplanName, ps.floorplan_slug AS floorplanSlug,
              ps.unit_id AS unitId, ps.floor AS floor,
              ps.bedrooms AS bedrooms, ps.bathrooms AS bathrooms, ps.sqft AS sqft, ps.price AS price,
              ps.available_date AS availableDate, ps.avail_note AS availNote,
              ps.special_tags AS specialTags, ps.scraped_at AS scrapedAt
            FROM price_snapshots ps
            JOIN complexes c ON c.id = ps.complex_id
            WHERE ps.scraped_at = (SELECT MAX(scraped_at) FROM price_snapshots WHERE (:cid IS NULL OR complex_id = :cid))
              AND (:cid IS NULL OR ps.complex_id = :cid)
              AND (:br IS NULL OR ps.bedrooms = :br)
              AND (:mp IS NULL OR ps.price <= :mp)
            ORDER BY ps.price ASC, ps.floorplan_name, ps.unit_id
            """, nativeQuery = true)
    List<LatestUnitProjection> findLatestUnits(
            @Param("cid") Integer complexId, @Param("br") Double bedrooms, @Param("mp") Integer maxPrice);

    @Query(value = """
            WITH latest AS (
              SELECT complex_id, MAX(scraped_at) AS ts FROM price_snapshots GROUP BY complex_id
            )
            SELECT ps.complex_id AS complexId, c.display_name AS complexName,
              ps.floorplan_name AS floorplanName, ps.floorplan_slug AS floorplanSlug,
              ps.bedrooms AS bedrooms, ps.bathrooms AS bathrooms, ps.sqft AS sqft,
              COUNT(DISTINCT ps.unit_id) AS availableUnits,
              MIN(ps.price) AS minPrice, MAX(ps.price) AS maxPrice, ROUND(AVG(ps.price)) AS avgPrice,
              (SELECT ps2.available_date FROM price_snapshots ps2
               JOIN latest l2 ON l2.complex_id = ps2.complex_id AND l2.ts = ps2.scraped_at
               WHERE ps2.complex_id = ps.complex_id AND ps2.floorplan_name = ps.floorplan_name
               ORDER BY ps2.price ASC LIMIT 1) AS earliestAvailable,
              ps.special_tags AS specialTags, l.ts AS scrapedAt, fm.image_url AS imageUrl, fm.floor AS urlFloor
            FROM price_snapshots ps
            JOIN latest l ON l.complex_id = ps.complex_id AND l.ts = ps.scraped_at
            JOIN complexes c ON c.id = ps.complex_id
            LEFT JOIN floorplan_meta fm ON fm.complex_id = ps.complex_id AND fm.floorplan_name = ps.floorplan_name
            WHERE (:cid IS NULL OR ps.complex_id = :cid)
              AND (NOT EXISTS (SELECT 1 FROM lease_term_prices ltp2 WHERE ltp2.complex_id = ps.complex_id)
                   OR EXISTS (SELECT 1 FROM lease_term_prices ltp2 WHERE ltp2.complex_id = ps.complex_id AND ltp2.lease_months >= 12))
            GROUP BY ps.complex_id, ps.floorplan_name
            ORDER BY ps.complex_id, minPrice ASC
            """, nativeQuery = true)
    List<FloorplanSummaryProjection> findFloorplanSummaries(@Param("cid") Integer complexId);

    @Query(value = """
            SELECT ps.complex_id AS complexId, c.display_name AS complexName,
              ps.unit_id AS unitId, ps.floor AS floor,
              ps.bedrooms AS bedrooms, ps.bathrooms AS bathrooms, ps.sqft AS sqft,
              ps.price AS price, ps.available_date AS availableDate, ps.avail_note AS availNote,
              ps.special_tags AS specialTags, ps.unit_features AS unitFeatures, ps.scraped_at AS scrapedAt
            FROM price_snapshots ps
            JOIN complexes c ON c.id = ps.complex_id
            WHERE ps.floorplan_name = :fp
              AND (:cid IS NULL OR ps.complex_id = :cid)
              AND ps.scraped_at = (
                SELECT MAX(scraped_at) FROM price_snapshots
                WHERE floorplan_name = :fp AND (:cid IS NULL OR complex_id = :cid)
              )
            ORDER BY ps.price ASC
            """, nativeQuery = true)
    List<UnitProjection> findUnitsByFloorplan(
            @Param("fp") String floorplanName, @Param("cid") Integer complexId);

    @Query(value = """
            SELECT p.complex_id AS complexId, c.display_name AS complexName,
              p.floorplan_name AS floorplanName, p.bedrooms AS bedrooms,
              p.bathrooms AS bathrooms, p.sqft AS sqft,
              MIN(p.price) AS allTimeMin, MAX(p.price) AS allTimeMax,
              (SELECT MIN(p2.price) FROM price_snapshots p2
               WHERE p2.floorplan_name = p.floorplan_name AND p2.complex_id = p.complex_id
                 AND p2.scraped_at = (SELECT MAX(scraped_at) FROM price_snapshots WHERE (:cid IS NULL OR complex_id = :cid))
              ) AS currentMin,
              COUNT(DISTINCT p.scraped_at) AS scrapeCount,
              COUNT(DISTINCT p.unit_id) AS totalUnitsSeen
            FROM price_snapshots p
            JOIN complexes c ON c.id = p.complex_id
            WHERE (:cid IS NULL OR p.complex_id = :cid)
            GROUP BY p.complex_id, p.floorplan_name
            ORDER BY currentMin ASC
            """, nativeQuery = true)
    List<StatsProjection> findStats(@Param("cid") Integer complexId);

    @Query(value = """
            SELECT complex_id AS complexId, floorplan_name AS floorplanName,
              unit_id AS unitId, floor AS floor, bedrooms AS bedrooms, bathrooms AS bathrooms,
              sqft AS sqft, price AS price, available_date AS availableDate,
              avail_note AS availNote, special_tags AS specialTags
            FROM price_snapshots
            WHERE scraped_at = (SELECT MAX(scraped_at) FROM price_snapshots WHERE (:cid IS NULL OR complex_id = :cid))
              AND price <= :mp
              AND (:cid IS NULL OR complex_id = :cid)
              AND (:br IS NULL OR bedrooms = :br)
            ORDER BY price ASC
            """, nativeQuery = true)
    List<AlertUnitProjection> findAlertUnits(
            @Param("mp") int maxPrice, @Param("cid") Integer complexId, @Param("br") Double bedrooms);

    @Query(value = """
            SELECT scraped_at AS scrapedAt, price AS price, available_date AS availableDate
            FROM price_snapshots
            WHERE unit_id = :uid
              AND scraped_at >= datetime('now', :lookback)
              AND (:cid IS NULL OR complex_id = :cid)
            ORDER BY scraped_at ASC
            """, nativeQuery = true)
    List<UnitHistoryProjection> findUnitHistory(
            @Param("uid") String unitId, @Param("cid") Integer complexId, @Param("lookback") String lookback);

    @Query(value = """
            SELECT scraped_at AS scrapedAt,
              MIN(price) AS minPrice, MAX(price) AS maxPrice,
              ROUND(AVG(price)) AS avgPrice, COUNT(unit_id) AS unitCount
            FROM price_snapshots
            WHERE floorplan_name = :fp
              AND scraped_at >= datetime('now', :lookback)
              AND (:cid IS NULL OR complex_id = :cid)
            GROUP BY scraped_at ORDER BY scraped_at ASC
            """, nativeQuery = true)
    List<HistoryProjection> findFloorplanHistory(
            @Param("fp") String floorplanName, @Param("cid") Integer complexId, @Param("lookback") String lookback);

    @Query(value = """
            WITH complex_latest AS (
              SELECT complex_id, MAX(scraped_at) AS latest_ts
              FROM price_snapshots WHERE (:cid IS NULL OR complex_id = :cid) GROUP BY complex_id
            ), latest_units AS (
              SELECT p.unit_id, p.complex_id FROM price_snapshots p
              JOIN complex_latest cl ON p.complex_id = cl.complex_id AND p.scraped_at = cl.latest_ts
            )
            SELECT p.unit_id AS unitId, p.floorplan_name AS floorplanName, p.floor AS floor,
              p.bedrooms AS bedrooms, p.price AS lastPrice,
              p.available_date AS lastAvailableDate, DATE(MAX(p.scraped_at)) AS lastSeen
            FROM price_snapshots p
            JOIN complex_latest cl ON p.complex_id = cl.complex_id
            LEFT JOIN latest_units lu ON p.unit_id = lu.unit_id AND p.complex_id = lu.complex_id
            WHERE p.scraped_at >= datetime(cl.latest_ts, :lookback)
              AND p.scraped_at < cl.latest_ts AND lu.unit_id IS NULL
            GROUP BY p.unit_id, p.floorplan_name ORDER BY p.floorplan_name, p.unit_id
            """, nativeQuery = true)
    List<RentedUnitProjection> findRentedUnits(
            @Param("cid") Integer complexId, @Param("lookback") String lookback);

    @Query(value = """
            WITH latest_snap AS (
              SELECT complex_id, MAX(scraped_at) AS ts FROM price_snapshots GROUP BY complex_id
            ), current_unit_prices AS (
              SELECT ps.complex_id, ps.floorplan_name, ps.unit_id, ps.price AS currentPrice
              FROM price_snapshots ps
              JOIN latest_snap ls ON ls.complex_id = ps.complex_id AND ls.ts = ps.scraped_at
              WHERE (:cid IS NULL OR ps.complex_id = :cid)
            ), first_unit_prices AS (
              SELECT ps.complex_id, ps.unit_id, ps.price AS firstPrice, ps.scraped_at AS firstSeen
              FROM price_snapshots ps WHERE ps.scraped_at = (
                SELECT MIN(scraped_at) FROM price_snapshots ps2
                WHERE ps2.complex_id = ps.complex_id AND ps2.unit_id = ps.unit_id
              )
            ), unit_changes AS (
              SELECT cp.complex_id, cp.floorplan_name, cp.unit_id, cp.currentPrice, fp.firstPrice,
                ABS(fp.firstPrice - cp.currentPrice) AS absChange,
                ROUND(ABS(CAST(fp.firstPrice - cp.currentPrice AS REAL)) / fp.firstPrice * 100, 1) AS changePct,
                CASE WHEN cp.currentPrice < fp.firstPrice THEN 'drop' ELSE 'increase' END AS direction,
                DATE(fp.firstSeen) AS firstSeen
              FROM current_unit_prices cp
              JOIN first_unit_prices fp ON fp.complex_id = cp.complex_id AND fp.unit_id = cp.unit_id
              WHERE cp.currentPrice != fp.firstPrice
            ), ranked AS (
              SELECT *, ROW_NUMBER() OVER (
                PARTITION BY complex_id, floorplan_name
                ORDER BY CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC, absChange DESC
              ) AS rn FROM unit_changes
            )
            SELECT complex_id AS complexId, floorplan_name AS floorplanName,
              unit_id AS bestUnitId, currentPrice AS currentMin, firstPrice AS baselineMin,
              absChange AS cumulativeDrop, changePct AS dropPct, direction, firstSeen
            FROM ranked WHERE rn = 1
            ORDER BY CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC, absChange DESC
            """, nativeQuery = true)
    List<PriceDropProjection> findPriceDrops(@Param("cid") Integer complexId);
}

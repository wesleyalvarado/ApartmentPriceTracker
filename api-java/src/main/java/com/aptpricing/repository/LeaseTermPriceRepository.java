package com.aptpricing.repository;

import com.aptpricing.entity.LeaseTermPrice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface LeaseTermPriceRepository extends JpaRepository<LeaseTermPrice, Integer> {

    // ── Projections ───────────────────────────────────────────────────────────

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
            SELECT DISTINCT lease_months
            FROM lease_term_prices
            WHERE (:cid IS NULL OR complex_id = :cid)
            ORDER BY lease_months DESC
            """, nativeQuery = true)
    List<Integer> findDistinctLeaseMonths(@Param("cid") Integer complexId);

    @Query(value = """
            WITH latest_snap AS (
              SELECT complex_id, MAX(scraped_at) AS ts FROM price_snapshots GROUP BY complex_id
            ), current_units AS (
              SELECT ps.complex_id, ps.unit_id, ps.floorplan_name, ps.floorplan_slug,
                     ps.bedrooms, ps.bathrooms, ps.sqft, ps.special_tags, ps.available_date
              FROM price_snapshots ps
              JOIN latest_snap ls ON ls.complex_id = ps.complex_id AND ls.ts = ps.scraped_at
            ), latest_lt AS (
              SELECT ltp.complex_id, ltp.unit_id, ltp.floorplan_name,
                     ltp.monthly_rent, ltp.move_in_date, MAX(ltp.scraped_at) AS scraped_at
              FROM lease_term_prices ltp
              WHERE ltp.lease_months = :term
                AND (:cid IS NULL OR ltp.complex_id = :cid)
              GROUP BY ltp.complex_id, ltp.unit_id, ltp.lease_months
            )
            SELECT ltp.complex_id AS complexId, c.display_name AS complexName,
              ltp.floorplan_name AS floorplanName,
              MIN(cu.floorplan_slug) AS floorplanSlug,
              MIN(cu.bedrooms) AS bedrooms, MIN(cu.bathrooms) AS bathrooms, MIN(cu.sqft) AS sqft,
              COUNT(DISTINCT ltp.unit_id) AS availableUnits,
              MIN(ltp.monthly_rent) AS minPrice, MAX(ltp.monthly_rent) AS maxPrice,
              ROUND(AVG(ltp.monthly_rent)) AS avgPrice,
              (SELECT COALESCE(NULLIF(ltp3.move_in_date,''), cu3.available_date)
               FROM latest_lt ltp3
               JOIN current_units cu3 ON cu3.complex_id = ltp3.complex_id AND cu3.unit_id = ltp3.unit_id
               WHERE ltp3.complex_id = ltp.complex_id AND ltp3.floorplan_name = ltp.floorplan_name
               ORDER BY ltp3.monthly_rent ASC LIMIT 1) AS earliestAvailable,
              MIN(cu.special_tags) AS specialTags, MAX(ltp.scraped_at) AS scrapedAt,
              fm.image_url AS imageUrl, fm.floor AS urlFloor
            FROM latest_lt ltp
            JOIN current_units cu ON cu.complex_id = ltp.complex_id AND cu.unit_id = ltp.unit_id
            JOIN complexes c ON c.id = ltp.complex_id
            LEFT JOIN floorplan_meta fm ON fm.complex_id = ltp.complex_id AND fm.floorplan_name = ltp.floorplan_name
            WHERE (:cid IS NULL OR ltp.complex_id = :cid)
            GROUP BY ltp.complex_id, ltp.floorplan_name
            ORDER BY ltp.complex_id, minPrice ASC
            """, nativeQuery = true)
    List<FloorplanSummaryProjection> findFloorplanSummariesByTerm(
            @Param("cid") Integer complexId, @Param("term") int leaseTerm);

    @Query(value = """
            WITH latest_snap AS (
              SELECT complex_id, MAX(scraped_at) AS ts
              FROM price_snapshots WHERE floorplan_name = :fp GROUP BY complex_id
            ), latest_lt AS (
              SELECT complex_id, unit_id, floorplan_name, monthly_rent, move_in_date, MAX(scraped_at) AS scraped_at
              FROM lease_term_prices
              WHERE lease_months = :term AND floorplan_name = :fp
                AND (:cid IS NULL OR complex_id = :cid)
              GROUP BY complex_id, unit_id, lease_months
            )
            SELECT ltp.complex_id AS complexId, c.display_name AS complexName, ltp.unit_id AS unitId,
              ps.floor AS floor, ps.bedrooms AS bedrooms, ps.bathrooms AS bathrooms, ps.sqft AS sqft,
              ltp.monthly_rent AS price,
              COALESCE(NULLIF(ltp.move_in_date,''), ps.available_date) AS availableDate,
              ps.avail_note AS availNote, ps.special_tags AS specialTags,
              ps.unit_features AS unitFeatures, ltp.scraped_at AS scrapedAt
            FROM latest_lt ltp
            JOIN complexes c ON c.id = ltp.complex_id
            JOIN (
              SELECT ps2.complex_id, ps2.unit_id, ps2.floor, ps2.bedrooms, ps2.bathrooms,
                     ps2.sqft, ps2.avail_note, ps2.available_date, ps2.special_tags, ps2.unit_features
              FROM price_snapshots ps2
              JOIN latest_snap ls ON ls.complex_id = ps2.complex_id AND ls.ts = ps2.scraped_at
              WHERE ps2.floorplan_name = :fp AND (:cid IS NULL OR ps2.complex_id = :cid)
            ) ps ON ps.complex_id = ltp.complex_id AND ps.unit_id = ltp.unit_id
            WHERE (:cid IS NULL OR ltp.complex_id = :cid)
            ORDER BY ltp.monthly_rent ASC
            """, nativeQuery = true)
    List<UnitProjection> findUnitsByFloorplanAndTerm(
            @Param("fp") String floorplanName, @Param("cid") Integer complexId, @Param("term") int leaseTerm);

    @Query(value = """
            WITH current_lt AS (
              SELECT lt.complex_id, lt.floorplan_name, lt.unit_id, lt.monthly_rent AS currentPrice
              FROM lease_term_prices lt
              WHERE lt.lease_months = :term AND (:cid IS NULL OR lt.complex_id = :cid)
                AND lt.scraped_at = (
                  SELECT MAX(lt2.scraped_at) FROM lease_term_prices lt2
                  WHERE lt2.complex_id = lt.complex_id AND lt2.unit_id = lt.unit_id AND lt2.lease_months = lt.lease_months
                )
            ), first_lt AS (
              SELECT lt.complex_id, lt.unit_id, lt.monthly_rent AS firstPrice, lt.scraped_at AS firstSeen
              FROM lease_term_prices lt
              WHERE lt.lease_months = :term
                AND lt.scraped_at = (
                  SELECT MIN(lt2.scraped_at) FROM lease_term_prices lt2
                  WHERE lt2.complex_id = lt.complex_id AND lt2.unit_id = lt.unit_id AND lt2.lease_months = lt.lease_months
                )
            ), unit_changes AS (
              SELECT cp.complex_id, cp.floorplan_name, cp.unit_id, cp.currentPrice, fp.firstPrice,
                ABS(fp.firstPrice - cp.currentPrice) AS absChange,
                ROUND(ABS(CAST(fp.firstPrice - cp.currentPrice AS REAL)) / fp.firstPrice * 100, 1) AS changePct,
                CASE WHEN cp.currentPrice < fp.firstPrice THEN 'drop' ELSE 'increase' END AS direction,
                DATE(fp.firstSeen) AS firstSeen
              FROM current_lt cp JOIN first_lt fp ON fp.complex_id = cp.complex_id AND fp.unit_id = cp.unit_id
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
    List<PriceDropProjection> findPriceDropsByTerm(
            @Param("cid") Integer complexId, @Param("term") int leaseTerm);
}

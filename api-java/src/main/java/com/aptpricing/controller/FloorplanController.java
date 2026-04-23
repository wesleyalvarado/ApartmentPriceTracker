package com.aptpricing.controller;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class FloorplanController {

    private final NamedParameterJdbcTemplate jdbc;

    public FloorplanController(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ── /api/floorplans ───────────────────────────────────────────────────────

    @GetMapping("/floorplans")
    public List<Map<String, Object>> getFloorplans(
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(name = "lease_term", required = false) Integer leaseTerm
    ) {
        var params = new MapSqlParameterSource();
        if (complexId != null) params.addValue("cid", complexId);

        if (leaseTerm != null && leaseTerm != 15) {
            // Verify lease term data exists
            String checkFilter = complexId != null ? "AND complex_id = :cid" : "";
            params.addValue("term", leaseTerm);
            Integer exists = jdbc.queryForObject(
                    "SELECT COUNT(1) FROM lease_term_prices WHERE lease_months = :term " + checkFilter,
                    params, Integer.class
            );
            if (exists == null || exists == 0) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                    "No lease term data for " + leaseTerm + " months. Run lease_terms.py first.");

            String cteFilter  = complexId != null ? "AND complex_id = :cid" : "";
            String joinFilter = complexId != null ? "AND ltp.complex_id = :cid" : "";

            return jdbc.queryForList(
                    "WITH latest_snap AS ( " +
                    "  SELECT complex_id, MAX(scraped_at) AS ts FROM price_snapshots GROUP BY complex_id " +
                    "), current_units AS ( " +
                    "  SELECT ps2.complex_id, ps2.unit_id, ps2.floorplan_name, ps2.floorplan_slug, " +
                    "         ps2.bedrooms, ps2.bathrooms, ps2.sqft, ps2.special_tags, ps2.available_date " +
                    "  FROM price_snapshots ps2 " +
                    "  JOIN latest_snap ls ON ls.complex_id = ps2.complex_id AND ls.ts = ps2.scraped_at " +
                    "), latest_lt AS ( " +
                    "  SELECT complex_id, unit_id, floorplan_name, lease_months, " +
                    "         monthly_rent, move_in_date, MAX(scraped_at) AS scraped_at " +
                    "  FROM lease_term_prices WHERE lease_months = :term " + cteFilter +
                    "  GROUP BY complex_id, unit_id, lease_months " +
                    ") " +
                    "SELECT ltp.complex_id, c.display_name AS complex_name, ltp.floorplan_name, " +
                    "  MIN(cu.floorplan_slug) AS floorplan_slug, MIN(cu.bedrooms) AS bedrooms, " +
                    "  MIN(cu.bathrooms) AS bathrooms, MIN(cu.sqft) AS sqft, " +
                    "  COUNT(DISTINCT ltp.unit_id) AS available_units, " +
                    "  MIN(ltp.monthly_rent) AS min_price, MAX(ltp.monthly_rent) AS max_price, " +
                    "  ROUND(AVG(ltp.monthly_rent)) AS avg_price, " +
                    "  ( SELECT COALESCE(NULLIF(ltp3.move_in_date,''), cu3.available_date) " +
                    "    FROM latest_lt ltp3 JOIN current_units cu3 " +
                    "      ON cu3.complex_id = ltp3.complex_id AND cu3.unit_id = ltp3.unit_id " +
                    "    WHERE ltp3.complex_id = ltp.complex_id AND ltp3.floorplan_name = ltp.floorplan_name " +
                    "    ORDER BY ltp3.monthly_rent ASC LIMIT 1 " +
                    "  ) AS earliest_available, " +
                    "  MIN(cu.special_tags) AS special_tags, MAX(ltp.scraped_at) AS scraped_at, " +
                    "  fm.image_url, fm.floor AS url_floor " +
                    "FROM latest_lt ltp " +
                    "JOIN current_units cu ON cu.complex_id = ltp.complex_id AND cu.unit_id = ltp.unit_id " +
                    "JOIN complexes c ON c.id = ltp.complex_id " +
                    "LEFT JOIN floorplan_meta fm ON fm.complex_id = ltp.complex_id AND fm.floorplan_name = ltp.floorplan_name " +
                    "WHERE 1=1 " + joinFilter +
                    " GROUP BY ltp.complex_id, ltp.floorplan_name ORDER BY ltp.complex_id, min_price ASC",
                    params
            );
        }

        // Default: standard price_snapshots pricing
        String filter = complexId != null ? "AND ps.complex_id = :cid" : "";
        return jdbc.queryForList(
                "WITH latest AS ( " +
                "  SELECT complex_id, MAX(scraped_at) AS ts FROM price_snapshots GROUP BY complex_id " +
                ") " +
                "SELECT ps.complex_id, c.display_name AS complex_name, ps.floorplan_name, " +
                "  ps.floorplan_slug, ps.bedrooms, ps.bathrooms, ps.sqft, " +
                "  COUNT(DISTINCT ps.unit_id) AS available_units, " +
                "  MIN(ps.price) AS min_price, MAX(ps.price) AS max_price, " +
                "  ROUND(AVG(ps.price)) AS avg_price, " +
                "  ( SELECT ps2.available_date FROM price_snapshots ps2 " +
                "    JOIN latest l2 ON l2.complex_id = ps2.complex_id AND l2.ts = ps2.scraped_at " +
                "    WHERE ps2.complex_id = ps.complex_id AND ps2.floorplan_name = ps.floorplan_name " +
                "    ORDER BY ps2.price ASC LIMIT 1 " +
                "  ) AS earliest_available, " +
                "  ps.special_tags, l.ts AS scraped_at, fm.image_url, fm.floor AS url_floor " +
                "FROM price_snapshots ps " +
                "JOIN latest l ON l.complex_id = ps.complex_id AND l.ts = ps.scraped_at " +
                "JOIN complexes c ON c.id = ps.complex_id " +
                "LEFT JOIN floorplan_meta fm ON fm.complex_id = ps.complex_id AND fm.floorplan_name = ps.floorplan_name " +
                "WHERE 1=1 " + filter +
                "  AND ( NOT EXISTS (SELECT 1 FROM lease_term_prices ltp2 WHERE ltp2.complex_id = ps.complex_id) " +
                "        OR EXISTS (SELECT 1 FROM lease_term_prices ltp2 WHERE ltp2.complex_id = ps.complex_id AND ltp2.lease_months >= 12) " +
                "  ) " +
                "GROUP BY ps.complex_id, ps.floorplan_name ORDER BY ps.complex_id, min_price ASC",
                params
        );
    }

    // ── /api/units/{floorplanName} ────────────────────────────────────────────

    @GetMapping("/units/{floorplanName}")
    public List<Map<String, Object>> getUnitsForFloorplan(
            @PathVariable String floorplanName,
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(name = "lease_term", required = false) Integer leaseTerm
    ) {
        var params = new MapSqlParameterSource("fp", floorplanName);
        if (complexId != null) params.addValue("cid", complexId);

        List<Map<String, Object>> rows;

        if (leaseTerm != null && leaseTerm != 15) {
            params.addValue("term", leaseTerm);
            String cteFilter  = complexId != null ? "AND complex_id = :cid" : "";
            String snapFilter = complexId != null ? "AND ps2.complex_id = :cid" : "";
            String joinFilter = complexId != null ? "AND ltp.complex_id = :cid" : "";

            rows = jdbc.queryForList(
                    "WITH latest_snap AS ( " +
                    "  SELECT complex_id, MAX(scraped_at) AS ts FROM price_snapshots " +
                    "  WHERE floorplan_name = :fp GROUP BY complex_id " +
                    "), latest_lt AS ( " +
                    "  SELECT complex_id, unit_id, floorplan_name, lease_months, " +
                    "         monthly_rent, move_in_date, MAX(scraped_at) AS scraped_at " +
                    "  FROM lease_term_prices WHERE lease_months = :term AND floorplan_name = :fp " + cteFilter +
                    "  GROUP BY complex_id, unit_id, lease_months " +
                    ") " +
                    "SELECT ltp.complex_id, c.display_name AS complex_name, ltp.unit_id, " +
                    "  ps.floor, ps.bedrooms, ps.bathrooms, ps.sqft, " +
                    "  ltp.monthly_rent AS price, " +
                    "  COALESCE(NULLIF(ltp.move_in_date,''), ps.available_date) AS available_date, " +
                    "  ps.avail_note, ps.special_tags, ps.unit_features, ltp.scraped_at " +
                    "FROM latest_lt ltp " +
                    "JOIN complexes c ON c.id = ltp.complex_id " +
                    "JOIN ( " +
                    "  SELECT ps2.complex_id, ps2.unit_id, ps2.floor, ps2.bedrooms, ps2.bathrooms, " +
                    "         ps2.sqft, ps2.avail_note, ps2.available_date, ps2.special_tags, ps2.unit_features " +
                    "  FROM price_snapshots ps2 " +
                    "  JOIN latest_snap ls ON ls.complex_id = ps2.complex_id AND ls.ts = ps2.scraped_at " +
                    "  WHERE ps2.floorplan_name = :fp " + snapFilter +
                    ") ps ON ps.complex_id = ltp.complex_id AND ps.unit_id = ltp.unit_id " +
                    "WHERE 1=1 " + joinFilter +
                    " ORDER BY ltp.monthly_rent ASC",
                    params
            );
            if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                    "No lease term data for " + leaseTerm + " months. Run lease_terms.py first.");
        } else {
            // Find latest timestamp for this floorplan
            String tsWhere = complexId != null ? "AND complex_id = :cid" : "";
            String ts = jdbc.queryForObject(
                    "SELECT MAX(scraped_at) FROM price_snapshots WHERE floorplan_name = :fp " + tsWhere,
                    params, String.class
            );
            if (ts == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                    "Floor plan '" + floorplanName + "' not found.");
            params.addValue("ts", ts);
            String filter = complexId != null ? "AND complex_id = :cid" : "";

            rows = jdbc.queryForList(
                    "SELECT ps.complex_id, c.display_name AS complex_name, " +
                    "ps.unit_id, ps.floor, ps.bedrooms, ps.bathrooms, ps.sqft, " +
                    "ps.price, ps.available_date, ps.avail_note, ps.special_tags, ps.unit_features, ps.scraped_at " +
                    "FROM price_snapshots ps " +
                    "JOIN complexes c ON c.id = ps.complex_id " +
                    "WHERE ps.scraped_at = :ts AND ps.floorplan_name = :fp " + filter +
                    " ORDER BY ps.price ASC",
                    params
            );
        }

        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                "Floor plan '" + floorplanName + "' not found.");
        return rows;
    }

    // ── /api/price-drops ─────────────────────────────────────────────────────

    @GetMapping("/price-drops")
    public List<Map<String, Object>> getPriceDrops(
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(name = "lease_term", required = false) Integer leaseTerm
    ) {
        var params = new MapSqlParameterSource();
        if (complexId != null) params.addValue("cid", complexId);

        if (leaseTerm != null && leaseTerm != 15) {
            params.addValue("term", leaseTerm);
            String filter = complexId != null ? "AND lt.complex_id = :cid" : "";

            return jdbc.queryForList(
                    "WITH current_lt AS ( " +
                    "  SELECT lt.complex_id, lt.floorplan_name, lt.unit_id, lt.monthly_rent AS current_price " +
                    "  FROM lease_term_prices lt WHERE lt.lease_months = :term " + filter +
                    "    AND lt.scraped_at = ( " +
                    "      SELECT MAX(lt2.scraped_at) FROM lease_term_prices lt2 " +
                    "      WHERE lt2.complex_id = lt.complex_id AND lt2.unit_id = lt.unit_id AND lt2.lease_months = lt.lease_months " +
                    "    ) " +
                    "), first_lt AS ( " +
                    "  SELECT lt.complex_id, lt.unit_id, lt.monthly_rent AS first_price, lt.scraped_at AS first_seen " +
                    "  FROM lease_term_prices lt WHERE lt.lease_months = :term " +
                    "    AND lt.scraped_at = ( " +
                    "      SELECT MIN(lt2.scraped_at) FROM lease_term_prices lt2 " +
                    "      WHERE lt2.complex_id = lt.complex_id AND lt2.unit_id = lt.unit_id AND lt2.lease_months = lt.lease_months " +
                    "    ) " +
                    "), unit_changes AS ( " +
                    "  SELECT cp.complex_id, cp.floorplan_name, cp.unit_id, cp.current_price, fp.first_price, " +
                    "    ABS(fp.first_price - cp.current_price) AS abs_change, " +
                    "    fp.first_price - cp.current_price AS price_change, " +
                    "    ROUND(ABS(CAST(fp.first_price - cp.current_price AS REAL)) / fp.first_price * 100, 1) AS change_pct, " +
                    "    CASE WHEN cp.current_price < fp.first_price THEN 'drop' ELSE 'increase' END AS direction, " +
                    "    DATE(fp.first_seen) AS first_seen " +
                    "  FROM current_lt cp JOIN first_lt fp ON fp.complex_id = cp.complex_id AND fp.unit_id = cp.unit_id " +
                    "  WHERE cp.current_price != fp.first_price " +
                    "), ranked AS ( " +
                    "  SELECT *, ROW_NUMBER() OVER ( " +
                    "    PARTITION BY complex_id, floorplan_name " +
                    "    ORDER BY CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC, abs_change DESC " +
                    "  ) AS rn FROM unit_changes " +
                    ") " +
                    "SELECT complex_id, floorplan_name, unit_id AS best_unit_id, " +
                    "  current_price AS current_min, first_price AS baseline_min, " +
                    "  abs_change AS cumulative_drop, change_pct AS drop_pct, direction, first_seen " +
                    "FROM ranked WHERE rn = 1 " +
                    "ORDER BY CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC, abs_change DESC",
                    params
            );
        }

        String filter = complexId != null ? "AND ps.complex_id = :cid" : "";
        return jdbc.queryForList(
                "WITH latest_snap AS ( " +
                "  SELECT complex_id, MAX(scraped_at) AS ts FROM price_snapshots GROUP BY complex_id " +
                "), current_unit_prices AS ( " +
                "  SELECT ps.complex_id, ps.floorplan_name, ps.unit_id, ps.price AS current_price " +
                "  FROM price_snapshots ps " +
                "  JOIN latest_snap ls ON ls.complex_id = ps.complex_id AND ls.ts = ps.scraped_at " +
                "  WHERE 1=1 " + filter +
                "), first_unit_prices AS ( " +
                "  SELECT ps.complex_id, ps.unit_id, ps.price AS first_price, ps.scraped_at AS first_seen " +
                "  FROM price_snapshots ps WHERE ps.scraped_at = ( " +
                "    SELECT MIN(scraped_at) FROM price_snapshots ps2 " +
                "    WHERE ps2.complex_id = ps.complex_id AND ps2.unit_id = ps.unit_id " +
                "  ) " +
                "), unit_changes AS ( " +
                "  SELECT cp.complex_id, cp.floorplan_name, cp.unit_id, cp.current_price, fp.first_price, " +
                "    ABS(fp.first_price - cp.current_price) AS abs_change, " +
                "    fp.first_price - cp.current_price AS price_change, " +
                "    ROUND(ABS(CAST(fp.first_price - cp.current_price AS REAL)) / fp.first_price * 100, 1) AS change_pct, " +
                "    CASE WHEN cp.current_price < fp.first_price THEN 'drop' ELSE 'increase' END AS direction, " +
                "    DATE(fp.first_seen) AS first_seen " +
                "  FROM current_unit_prices cp JOIN first_unit_prices fp " +
                "    ON fp.complex_id = cp.complex_id AND fp.unit_id = cp.unit_id " +
                "  WHERE cp.current_price != fp.first_price " +
                "), ranked AS ( " +
                "  SELECT *, ROW_NUMBER() OVER ( " +
                "    PARTITION BY complex_id, floorplan_name " +
                "    ORDER BY CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC, abs_change DESC " +
                "  ) AS rn FROM unit_changes " +
                ") " +
                "SELECT complex_id, floorplan_name, unit_id AS best_unit_id, " +
                "  current_price AS current_min, first_price AS baseline_min, " +
                "  abs_change AS cumulative_drop, change_pct AS drop_pct, direction, first_seen " +
                "FROM ranked WHERE rn = 1 " +
                "ORDER BY CASE WHEN direction = 'drop' THEN 0 ELSE 1 END ASC, abs_change DESC",
                params
        );
    }
}

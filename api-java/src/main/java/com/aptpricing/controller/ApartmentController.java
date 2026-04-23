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
public class ApartmentController {

    private final NamedParameterJdbcTemplate jdbc;

    public ApartmentController(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ── helpers ──────────────────────────────────────────────────────────────

    private String latestTs(Integer complexId) {
        var params = new MapSqlParameterSource();
        String where = complexId != null ? "WHERE complex_id = :cid" : "";
        if (complexId != null) params.addValue("cid", complexId);
        String ts = jdbc.queryForObject(
                "SELECT MAX(scraped_at) FROM price_snapshots " + where,
                params, String.class
        );
        if (ts == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No scrape data found.");
        return ts;
    }

    // ── /api/latest ──────────────────────────────────────────────────────────

    @GetMapping("/latest")
    public List<Map<String, Object>> getLatest(
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(required = false) Double bedrooms,
            @RequestParam(name = "max_price", required = false) Integer maxPrice
    ) {
        String ts = latestTs(complexId);
        var params = new MapSqlParameterSource("ts", ts);
        var where = new StringBuilder("ps.scraped_at = :ts");

        if (complexId != null) { where.append(" AND ps.complex_id = :cid"); params.addValue("cid", complexId); }
        if (bedrooms  != null) { where.append(" AND ps.bedrooms = :br");    params.addValue("br", bedrooms); }
        if (maxPrice  != null) { where.append(" AND ps.price <= :mp");      params.addValue("mp", maxPrice); }

        return jdbc.queryForList(
                "SELECT ps.complex_id, c.display_name AS complex_name, " +
                "ps.floorplan_name, ps.floorplan_slug, ps.unit_id, ps.floor, " +
                "ps.bedrooms, ps.bathrooms, ps.sqft, ps.price, " +
                "ps.available_date, ps.avail_note, ps.special_tags, ps.scraped_at " +
                "FROM price_snapshots ps " +
                "JOIN complexes c ON c.id = ps.complex_id " +
                "WHERE " + where +
                " ORDER BY ps.price ASC, ps.floorplan_name, ps.unit_id",
                params
        );
    }

    // ── /api/stats ───────────────────────────────────────────────────────────

    @GetMapping("/stats")
    public List<Map<String, Object>> getStats(
            @RequestParam(name = "complex_id", required = false) Integer complexId
    ) {
        String ts = latestTs(complexId);
        var params = new MapSqlParameterSource("ts", ts);
        String where = complexId != null ? "AND p.complex_id = :cid" : "";
        if (complexId != null) params.addValue("cid", complexId);

        return jdbc.queryForList(
                "SELECT p.complex_id, c.display_name AS complex_name, " +
                "p.floorplan_name, p.bedrooms, p.bathrooms, p.sqft, " +
                "MIN(p.price) AS all_time_min, MAX(p.price) AS all_time_max, " +
                "( SELECT MIN(p2.price) FROM price_snapshots p2 " +
                "  WHERE p2.floorplan_name = p.floorplan_name " +
                "    AND p2.complex_id = p.complex_id AND p2.scraped_at = :ts " +
                ") AS current_min, " +
                "COUNT(DISTINCT p.scraped_at) AS scrape_count, " +
                "COUNT(DISTINCT p.unit_id)    AS total_units_seen " +
                "FROM price_snapshots p " +
                "JOIN complexes c ON c.id = p.complex_id " +
                "WHERE 1=1 " + where +
                " GROUP BY p.complex_id, p.floorplan_name " +
                "ORDER BY current_min ASC",
                params
        );
    }

    // ── /api/alerts ──────────────────────────────────────────────────────────

    @GetMapping("/alerts")
    public Map<String, Object> getAlerts(
            @RequestParam(name = "max_price") int maxPrice,
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(required = false) Double bedrooms
    ) {
        String ts = latestTs(complexId);
        var params = new MapSqlParameterSource("ts", ts).addValue("mp", maxPrice);
        var where = new StringBuilder("scraped_at = :ts AND price <= :mp");

        if (complexId != null) { where.append(" AND complex_id = :cid"); params.addValue("cid", complexId); }
        if (bedrooms  != null) { where.append(" AND bedrooms = :br");    params.addValue("br", bedrooms); }

        List<Map<String, Object>> matches = jdbc.queryForList(
                "SELECT complex_id, floorplan_name, unit_id, floor, bedrooms, bathrooms, " +
                "sqft, price, available_date, avail_note, special_tags " +
                "FROM price_snapshots WHERE " + where + " ORDER BY price ASC",
                params
        );
        return Map.of("threshold", maxPrice, "matches", matches);
    }

    // ── /api/history/{unit_id} ───────────────────────────────────────────────

    @GetMapping("/history/{unitId}")
    public List<Map<String, Object>> getUnitHistory(
            @PathVariable String unitId,
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(defaultValue = "30") int days
    ) {
        var params = new MapSqlParameterSource("uid", unitId)
                .addValue("lookback", "-" + days + " days");
        String where = complexId != null ? "AND complex_id = :cid" : "";
        if (complexId != null) params.addValue("cid", complexId);

        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT scraped_at, price, available_date FROM price_snapshots " +
                "WHERE unit_id = :uid " +
                "  AND scraped_at >= datetime('now', :lookback) " + where +
                " ORDER BY scraped_at ASC",
                params
        );
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                "No history found for unit '" + unitId + "'.");
        return rows;
    }

    // ── /api/history/floorplan/{floorplan_name} ──────────────────────────────

    @GetMapping("/history/floorplan/{floorplanName}")
    public List<Map<String, Object>> getFloorplanHistory(
            @PathVariable String floorplanName,
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(defaultValue = "30") int days
    ) {
        var params = new MapSqlParameterSource("fp", floorplanName)
                .addValue("lookback", "-" + days + " days");
        String where = complexId != null ? "AND complex_id = :cid" : "";
        if (complexId != null) params.addValue("cid", complexId);

        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT scraped_at, MIN(price) AS min_price, MAX(price) AS max_price, " +
                "ROUND(AVG(price)) AS avg_price, COUNT(unit_id) AS unit_count " +
                "FROM price_snapshots " +
                "WHERE floorplan_name = :fp " +
                "  AND scraped_at >= datetime('now', :lookback) " + where +
                " GROUP BY scraped_at ORDER BY scraped_at ASC",
                params
        );
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                "No history found for floor plan '" + floorplanName + "'.");
        return rows;
    }

    // ── /api/rented ──────────────────────────────────────────────────────────

    @GetMapping("/rented")
    public List<Map<String, Object>> getRented(
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(defaultValue = "14") int days
    ) {
        var params = new MapSqlParameterSource("lookback", "-" + days + " days");
        String complexWhere = complexId != null ? "WHERE complex_id = :cid" : "";
        if (complexId != null) params.addValue("cid", complexId);

        return jdbc.queryForList(
                "WITH complex_latest AS ( " +
                "  SELECT complex_id, MAX(scraped_at) AS latest_ts " +
                "  FROM price_snapshots " + complexWhere + " GROUP BY complex_id " +
                "), latest_units AS ( " +
                "  SELECT p.unit_id, p.complex_id FROM price_snapshots p " +
                "  JOIN complex_latest cl ON p.complex_id = cl.complex_id AND p.scraped_at = cl.latest_ts " +
                ") " +
                "SELECT p.unit_id, p.floorplan_name, p.floor, p.bedrooms, " +
                "p.price AS last_price, p.available_date AS last_available_date, " +
                "DATE(MAX(p.scraped_at)) AS last_seen " +
                "FROM price_snapshots p " +
                "JOIN complex_latest cl ON p.complex_id = cl.complex_id " +
                "LEFT JOIN latest_units lu ON p.unit_id = lu.unit_id AND p.complex_id = lu.complex_id " +
                "WHERE p.scraped_at >= datetime(cl.latest_ts, :lookback) " +
                "  AND p.scraped_at < cl.latest_ts AND lu.unit_id IS NULL " +
                "GROUP BY p.unit_id, p.floorplan_name " +
                "ORDER BY p.floorplan_name, p.unit_id",
                params
        );
    }
}

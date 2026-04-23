package com.aptpricing.controller;

import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ComplexController {

    private final NamedParameterJdbcTemplate jdbc;

    public ComplexController(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/complexes")
    public List<Map<String, Object>> listComplexes() {
        return jdbc.queryForList(
                "SELECT id, name, display_name, city, state, url FROM complexes ORDER BY id",
                Map.of()
        );
    }

    @GetMapping("/scrapes")
    public List<Map<String, Object>> listScrapes(
            @RequestParam(name = "complex_id", required = false) Integer complexId
    ) {
        var params = new MapSqlParameterSource();
        String where = "";
        if (complexId != null) {
            where = "WHERE complex_id = :cid ";
            params.addValue("cid", complexId);
        }
        return jdbc.queryForList(
                "SELECT scraped_at, COUNT(*) as unit_count " +
                "FROM price_snapshots " + where +
                "GROUP BY scraped_at ORDER BY scraped_at DESC",
                params
        );
    }

    @GetMapping("/lease_terms")
    public List<Integer> getLeaseTerms(
            @RequestParam(name = "complex_id", required = false) Integer complexId
    ) {
        var params = new MapSqlParameterSource();
        String where = "";
        if (complexId != null) {
            where = "WHERE complex_id = :cid ";
            params.addValue("cid", complexId);
        }
        return jdbc.queryForList(
                "SELECT DISTINCT lease_months FROM lease_term_prices " + where +
                "ORDER BY lease_months DESC",
                params,
                Integer.class
        );
    }
}

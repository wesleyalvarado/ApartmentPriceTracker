package com.aptpricing.controller;

import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/house-prices")
public class HousePriceController {

    private final NamedParameterJdbcTemplate jdbc;

    public HousePriceController(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private boolean tablesExist() {
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='zhvi_monthly'",
                Map.of(), Integer.class
        );
        return count != null && count > 0;
    }

    @GetMapping("/summary")
    public List<Map<String, Object>> getSummary() {
        if (!tablesExist()) return List.of();
        return jdbc.queryForList(
                "SELECT z.zip_code, zn.display_name, zn.neighborhoods, " +
                "  z.median_value AS zhvi_current, z.month AS zhvi_month, " +
                "  r.median_list_price, r.median_sale_price, r.inventory, " +
                "  r.days_on_market, r.new_listings, r.period_begin AS redfin_week " +
                "FROM ( " +
                "  SELECT zip_code, median_value, month FROM zhvi_monthly " +
                "  WHERE home_type = 'all_middle_tier' " +
                "    AND (zip_code, month) IN ( " +
                "      SELECT zip_code, MAX(month) FROM zhvi_monthly " +
                "      WHERE home_type = 'all_middle_tier' GROUP BY zip_code " +
                "    ) " +
                ") z " +
                "LEFT JOIN ( " +
                "  SELECT zip_code, median_list_price, median_sale_price, " +
                "         inventory, days_on_market, new_listings, period_begin " +
                "  FROM redfin_weekly " +
                "  WHERE (zip_code, period_begin) IN ( " +
                "    SELECT zip_code, MAX(period_begin) FROM redfin_weekly GROUP BY zip_code " +
                "  ) " +
                ") r ON z.zip_code = r.zip_code " +
                "LEFT JOIN zip_neighborhoods zn ON z.zip_code = zn.zip_code " +
                "ORDER BY z.zip_code",
                Map.of()
        );
    }

    @GetMapping("/zhvi")
    public List<Map<String, Object>> getZhvi(
            @RequestParam(name = "zip_code", required = false) String zipCode,
            @RequestParam(name = "home_type", defaultValue = "all_middle_tier") String homeType,
            @RequestParam(defaultValue = "24") int months
    ) {
        if (!tablesExist()) return List.of();
        var params = new MapSqlParameterSource("homeType", homeType)
                .addValue("lookback", "-" + months + " months");
        String filter = zipCode != null ? "AND zip_code = :zip" : "";
        if (zipCode != null) params.addValue("zip", zipCode);

        return jdbc.queryForList(
                "SELECT zip_code, month, median_value, home_type FROM zhvi_monthly " +
                "WHERE home_type = :homeType AND month >= date('now', :lookback) " + filter +
                " ORDER BY zip_code, month",
                params
        );
    }

    @GetMapping("/redfin")
    public List<Map<String, Object>> getRedfin(
            @RequestParam(name = "zip_code", required = false) String zipCode,
            @RequestParam(defaultValue = "12") int months
    ) {
        if (!tablesExist()) return List.of();
        var params = new MapSqlParameterSource("lookback", "-" + months + " months");
        String filter = zipCode != null ? "AND zip_code = :zip" : "";
        if (zipCode != null) params.addValue("zip", zipCode);

        return jdbc.queryForList(
                "SELECT zip_code, period_begin, period_end, median_sale_price, median_list_price, " +
                "  homes_sold, new_listings, inventory, days_on_market, sale_to_list_ratio, median_ppsf " +
                "FROM redfin_weekly " +
                "WHERE period_begin >= date('now', :lookback) " + filter +
                " ORDER BY zip_code, period_begin",
                params
        );
    }

    @GetMapping("/mortgage-check")
    public Map<String, Object> mortgageCheck(
            @RequestParam(defaultValue = "3500") double maxMonthly,
            @RequestParam(defaultValue = "6.3") double rate,
            @RequestParam(defaultValue = "20") double downPct,
            @RequestParam(defaultValue = "2.2") double taxRate,
            @RequestParam(defaultValue = "2100") double insuranceAnnual
    ) {
        double monthlyInsurance = insuranceAnnual / 12;
        double r = (rate / 100) / 12;
        int n = 360;
        double factor = (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
        double priceCoefficient = (1 - downPct / 100) * factor + (taxRate / 100 / 12);
        double maxPrice = (maxMonthly - monthlyInsurance) / priceCoefficient;

        return Map.of(
                "max_purchase_price",  Math.round(maxPrice),
                "down_payment_amount", Math.round(maxPrice * downPct / 100),
                "loan_amount",         Math.round(maxPrice * (1 - downPct / 100)),
                "monthly_pi",          Math.round(maxPrice * (1 - downPct / 100) * factor),
                "monthly_tax",         Math.round(maxPrice * taxRate / 100 / 12),
                "monthly_insurance",   Math.round(monthlyInsurance),
                "total_monthly",       Math.round(maxMonthly)
        );
    }
}

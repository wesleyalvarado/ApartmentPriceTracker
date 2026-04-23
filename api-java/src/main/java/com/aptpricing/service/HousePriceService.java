package com.aptpricing.service;

import com.aptpricing.dto.MortgageCheckDto;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

// House price tables (zhvi_monthly, redfin_weekly, zip_neighborhoods) have no JPA entities —
// they're ancillary market data. NamedParameterJdbcTemplate is a common choice alongside
// JPA for tables that don't fit the entity model or that require complex native queries.
@Service
public class HousePriceService {

    private final NamedParameterJdbcTemplate jdbc;

    public HousePriceService(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public boolean tablesExist() {
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='zhvi_monthly'",
                Map.of(), Integer.class);
        return count != null && count > 0;
    }

    public List<Map<String, Object>> getSummary() {
        if (!tablesExist()) return List.of();
        return jdbc.queryForList(
                "SELECT z.zip_code, zn.display_name, zn.neighborhoods, " +
                "  z.median_value AS zhvi_current, z.month AS zhvi_month, " +
                "  r.median_list_price, r.median_sale_price, r.inventory, " +
                "  r.days_on_market, r.new_listings, r.period_begin AS redfin_week " +
                "FROM (SELECT zip_code, median_value, month FROM zhvi_monthly " +
                "      WHERE home_type = 'all_middle_tier' " +
                "        AND (zip_code, month) IN (SELECT zip_code, MAX(month) FROM zhvi_monthly " +
                "             WHERE home_type = 'all_middle_tier' GROUP BY zip_code)) z " +
                "LEFT JOIN (SELECT zip_code, median_list_price, median_sale_price, inventory, " +
                "                  days_on_market, new_listings, period_begin FROM redfin_weekly " +
                "           WHERE (zip_code, period_begin) IN (SELECT zip_code, MAX(period_begin) " +
                "                FROM redfin_weekly GROUP BY zip_code)) r ON z.zip_code = r.zip_code " +
                "LEFT JOIN zip_neighborhoods zn ON z.zip_code = zn.zip_code " +
                "ORDER BY z.zip_code", Map.of());
    }

    public List<Map<String, Object>> getZhvi(String zipCode, String homeType, int months) {
        if (!tablesExist()) return List.of();
        var params = new MapSqlParameterSource("homeType", homeType)
                .addValue("lookback", "-" + months + " months");
        String filter = zipCode != null ? "AND zip_code = :zip" : "";
        if (zipCode != null) params.addValue("zip", zipCode);
        return jdbc.queryForList(
                "SELECT zip_code, month, median_value, home_type FROM zhvi_monthly " +
                "WHERE home_type = :homeType AND month >= date('now', :lookback) " + filter +
                " ORDER BY zip_code, month", params);
    }

    public List<Map<String, Object>> getRedfin(String zipCode, int months) {
        if (!tablesExist()) return List.of();
        var params = new MapSqlParameterSource("lookback", "-" + months + " months");
        String filter = zipCode != null ? "AND zip_code = :zip" : "";
        if (zipCode != null) params.addValue("zip", zipCode);
        return jdbc.queryForList(
                "SELECT zip_code, period_begin, period_end, median_sale_price, median_list_price, " +
                "  homes_sold, new_listings, inventory, days_on_market, sale_to_list_ratio, median_ppsf " +
                "FROM redfin_weekly WHERE period_begin >= date('now', :lookback) " + filter +
                " ORDER BY zip_code, period_begin", params);
    }

    public MortgageCheckDto getMortgageCheck(double maxMonthly, double rate, double downPct,
                                             double taxRate, double insuranceAnnual) {
        double monthlyInsurance = insuranceAnnual / 12;
        double r = (rate / 100) / 12;
        int n = 360;
        double factor = (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
        double priceCoeff = (1 - downPct / 100) * factor + (taxRate / 100 / 12);
        double maxPrice = (maxMonthly - monthlyInsurance) / priceCoeff;
        return new MortgageCheckDto(
                Math.round(maxPrice),
                Math.round(maxPrice * downPct / 100),
                Math.round(maxPrice * (1 - downPct / 100)),
                Math.round(maxPrice * (1 - downPct / 100) * factor),
                Math.round(maxPrice * taxRate / 100 / 12),
                Math.round(monthlyInsurance),
                Math.round(maxMonthly));
    }
}

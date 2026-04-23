package com.aptpricing.controller;

import com.aptpricing.dto.MortgageCheckDto;
import com.aptpricing.service.HousePriceService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/house-prices")
public class HousePriceController {

    private final HousePriceService housePriceService;

    public HousePriceController(HousePriceService housePriceService) {
        this.housePriceService = housePriceService;
    }

    @GetMapping("/summary")
    public List<Map<String, Object>> getSummary() {
        return housePriceService.getSummary();
    }

    @GetMapping("/zhvi")
    public List<Map<String, Object>> getZhvi(
            @RequestParam(name = "zip_code", required = false) String zipCode,
            @RequestParam(name = "home_type", defaultValue = "all_middle_tier") String homeType,
            @RequestParam(defaultValue = "24") int months
    ) {
        return housePriceService.getZhvi(zipCode, homeType, months);
    }

    @GetMapping("/redfin")
    public List<Map<String, Object>> getRedfin(
            @RequestParam(name = "zip_code", required = false) String zipCode,
            @RequestParam(defaultValue = "12") int months
    ) {
        return housePriceService.getRedfin(zipCode, months);
    }

    @GetMapping("/mortgage-check")
    public MortgageCheckDto mortgageCheck(
            @RequestParam(defaultValue = "3500") double maxMonthly,
            @RequestParam(defaultValue = "6.3") double rate,
            @RequestParam(defaultValue = "20") double downPct,
            @RequestParam(defaultValue = "2.2") double taxRate,
            @RequestParam(defaultValue = "2100") double insuranceAnnual
    ) {
        return housePriceService.getMortgageCheck(maxMonthly, rate, downPct, taxRate, insuranceAnnual);
    }
}

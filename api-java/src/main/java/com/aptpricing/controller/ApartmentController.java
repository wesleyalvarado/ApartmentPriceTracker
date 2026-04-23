package com.aptpricing.controller;

import com.aptpricing.dto.AlertsResponseDto;
import com.aptpricing.dto.PriceHistoryDto;
import com.aptpricing.dto.RentedUnitDto;
import com.aptpricing.dto.StatsDto;
import com.aptpricing.dto.UnitDto;
import com.aptpricing.service.ApartmentService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api")
public class ApartmentController {

    private final ApartmentService apartmentService;

    public ApartmentController(ApartmentService apartmentService) {
        this.apartmentService = apartmentService;
    }

    @GetMapping("/latest")
    public List<UnitDto> getLatest(
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(required = false) Double bedrooms,
            @RequestParam(name = "max_price", required = false) Integer maxPrice
    ) {
        return apartmentService.getLatest(complexId, bedrooms, maxPrice);
    }

    @GetMapping("/stats")
    public List<StatsDto> getStats(
            @RequestParam(name = "complex_id", required = false) Integer complexId
    ) {
        return apartmentService.getStats(complexId);
    }

    @GetMapping("/alerts")
    public AlertsResponseDto getAlerts(
            @RequestParam(name = "max_price") int maxPrice,
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(required = false) Double bedrooms
    ) {
        return apartmentService.getAlerts(maxPrice, complexId, bedrooms);
    }

    @GetMapping("/history/{unitId}")
    public List<PriceHistoryDto> getUnitHistory(
            @PathVariable String unitId,
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(defaultValue = "30") int days
    ) {
        return apartmentService.getUnitHistory(unitId, complexId, days);
    }

    @GetMapping("/history/floorplan/{floorplanName}")
    public List<PriceHistoryDto> getFloorplanHistory(
            @PathVariable String floorplanName,
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(defaultValue = "30") int days
    ) {
        return apartmentService.getFloorplanHistory(floorplanName, complexId, days);
    }

    @GetMapping("/rented")
    public List<RentedUnitDto> getRented(
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(defaultValue = "14") int days
    ) {
        return apartmentService.getRented(complexId, days);
    }
}

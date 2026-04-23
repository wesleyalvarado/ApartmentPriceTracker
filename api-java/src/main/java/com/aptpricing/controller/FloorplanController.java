package com.aptpricing.controller;

import com.aptpricing.dto.FloorplanSummaryDto;
import com.aptpricing.dto.PriceDropDto;
import com.aptpricing.dto.UnitDto;
import com.aptpricing.service.FloorplanService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api")
public class FloorplanController {

    private final FloorplanService floorplanService;

    public FloorplanController(FloorplanService floorplanService) {
        this.floorplanService = floorplanService;
    }

    @GetMapping("/floorplans")
    public List<FloorplanSummaryDto> getFloorplans(
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(name = "lease_term", required = false) Integer leaseTerm
    ) {
        return floorplanService.getFloorplans(complexId, leaseTerm);
    }

    @GetMapping("/units/{floorplanName}")
    public List<UnitDto> getUnitsForFloorplan(
            @PathVariable String floorplanName,
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(name = "lease_term", required = false) Integer leaseTerm
    ) {
        return floorplanService.getUnitsForFloorplan(floorplanName, complexId, leaseTerm);
    }

    @GetMapping("/price-drops")
    public List<PriceDropDto> getPriceDrops(
            @RequestParam(name = "complex_id", required = false) Integer complexId,
            @RequestParam(name = "lease_term", required = false) Integer leaseTerm
    ) {
        return floorplanService.getPriceDrops(complexId, leaseTerm);
    }
}

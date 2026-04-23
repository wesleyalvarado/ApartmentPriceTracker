package com.aptpricing.controller;

import com.aptpricing.dto.ComplexDto;
import com.aptpricing.dto.ScrapeDto;
import com.aptpricing.service.ComplexService;
import com.aptpricing.service.FloorplanService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api")
public class ComplexController {

    private final ComplexService complexService;
    private final FloorplanService floorplanService;

    public ComplexController(ComplexService complexService, FloorplanService floorplanService) {
        this.complexService = complexService;
        this.floorplanService = floorplanService;
    }

    @GetMapping("/complexes")
    public List<ComplexDto> listComplexes() {
        return complexService.getComplexes();
    }

    @GetMapping("/scrapes")
    public List<ScrapeDto> listScrapes(
            @RequestParam(name = "complex_id", required = false) Integer complexId
    ) {
        return complexService.getScrapes(complexId);
    }

    @GetMapping("/lease_terms")
    public List<Integer> getLeaseTerms(
            @RequestParam(name = "complex_id", required = false) Integer complexId
    ) {
        return floorplanService.getLeaseTerms(complexId);
    }
}

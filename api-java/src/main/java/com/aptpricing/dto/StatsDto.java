package com.aptpricing.dto;

public record StatsDto(
        Integer complexId,
        String complexName,
        String floorplanName,
        Double bedrooms,
        Double bathrooms,
        Integer sqft,
        Integer allTimeMin,
        Integer allTimeMax,
        Integer currentMin,
        Long scrapeCount,
        Long totalUnitsSeen
) {}

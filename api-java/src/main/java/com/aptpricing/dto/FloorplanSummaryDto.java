package com.aptpricing.dto;

public record FloorplanSummaryDto(
        Integer complexId,
        String complexName,
        String floorplanName,
        String floorplanSlug,
        Double bedrooms,
        Double bathrooms,
        Integer sqft,
        Long availableUnits,
        Integer minPrice,
        Integer maxPrice,
        Long avgPrice,
        String earliestAvailable,
        String specialTags,
        String scrapedAt,
        String imageUrl,
        Integer urlFloor
) {}

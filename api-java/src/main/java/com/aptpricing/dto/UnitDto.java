package com.aptpricing.dto;

public record UnitDto(
        Integer complexId,
        String complexName,
        String floorplanName,
        String floorplanSlug,
        String unitId,
        Integer floor,
        Double bedrooms,
        Double bathrooms,
        Integer sqft,
        Integer price,
        String availableDate,
        String availNote,
        String specialTags,
        String unitFeatures,
        String scrapedAt
) {}

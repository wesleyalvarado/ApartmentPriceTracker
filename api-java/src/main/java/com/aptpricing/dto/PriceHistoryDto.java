package com.aptpricing.dto;

public record PriceHistoryDto(
        String scrapedAt,
        Integer minPrice,
        Integer maxPrice,
        Long avgPrice,
        Long unitCount
) {}

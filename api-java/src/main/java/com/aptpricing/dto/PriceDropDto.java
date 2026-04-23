package com.aptpricing.dto;

public record PriceDropDto(
        Integer complexId,
        String floorplanName,
        String bestUnitId,
        Integer currentMin,
        Integer baselineMin,
        Integer cumulativeDrop,
        Double dropPct,
        String direction,
        String firstSeen
) {}

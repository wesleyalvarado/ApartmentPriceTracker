package com.aptpricing.dto;

public record RentedUnitDto(
        String unitId,
        String floorplanName,
        Integer floor,
        Double bedrooms,
        Integer lastPrice,
        String lastAvailableDate,
        String lastSeen
) {}

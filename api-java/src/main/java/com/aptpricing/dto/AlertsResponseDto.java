package com.aptpricing.dto;

import java.util.List;

public record AlertsResponseDto(
        int threshold,
        List<UnitDto> matches
) {}

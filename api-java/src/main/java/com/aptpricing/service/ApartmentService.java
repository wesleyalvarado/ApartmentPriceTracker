package com.aptpricing.service;

import com.aptpricing.dto.AlertsResponseDto;
import com.aptpricing.dto.PriceHistoryDto;
import com.aptpricing.dto.RentedUnitDto;
import com.aptpricing.dto.StatsDto;
import com.aptpricing.dto.UnitDto;
import com.aptpricing.repository.PriceSnapshotRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
public class ApartmentService {

    private final PriceSnapshotRepository snapshotRepo;

    public ApartmentService(PriceSnapshotRepository snapshotRepo) {
        this.snapshotRepo = snapshotRepo;
    }

    public List<UnitDto> getLatest(Integer complexId, Double bedrooms, Integer maxPrice) {
        return snapshotRepo.findLatestUnits(complexId, bedrooms, maxPrice).stream()
                .map(p -> new UnitDto(p.getComplexId(), p.getComplexName(), p.getFloorplanName(),
                        p.getFloorplanSlug(), p.getUnitId(), p.getFloor(),
                        p.getBedrooms(), p.getBathrooms(), p.getSqft(), p.getPrice(),
                        p.getAvailableDate(), p.getAvailNote(), p.getSpecialTags(), null, p.getScrapedAt()))
                .toList();
    }

    public List<StatsDto> getStats(Integer complexId) {
        return snapshotRepo.findStats(complexId).stream()
                .map(p -> new StatsDto(p.getComplexId(), p.getComplexName(), p.getFloorplanName(),
                        p.getBedrooms(), p.getBathrooms(), p.getSqft(),
                        p.getAllTimeMin(), p.getAllTimeMax(), p.getCurrentMin(),
                        p.getScrapeCount(), p.getTotalUnitsSeen()))
                .toList();
    }

    public AlertsResponseDto getAlerts(int maxPrice, Integer complexId, Double bedrooms) {
        List<UnitDto> matches = snapshotRepo.findAlertUnits(maxPrice, complexId, bedrooms).stream()
                .map(p -> new UnitDto(p.getComplexId(), null, p.getFloorplanName(), null,
                        p.getUnitId(), p.getFloor(), p.getBedrooms(), p.getBathrooms(), p.getSqft(),
                        p.getPrice(), p.getAvailableDate(), p.getAvailNote(), p.getSpecialTags(), null, null))
                .toList();
        return new AlertsResponseDto(maxPrice, matches);
    }

    public List<PriceHistoryDto> getUnitHistory(String unitId, Integer complexId, int days) {
        String lookback = "-" + days + " days";
        List<PriceHistoryDto> rows = snapshotRepo.findUnitHistory(unitId, complexId, lookback).stream()
                .map(p -> new PriceHistoryDto(p.getScrapedAt(), p.getPrice(), p.getPrice(), (long) p.getPrice(), 1L))
                .toList();
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                "No history found for unit '" + unitId + "'.");
        return rows;
    }

    public List<PriceHistoryDto> getFloorplanHistory(String floorplanName, Integer complexId, int days) {
        String lookback = "-" + days + " days";
        List<PriceHistoryDto> rows = snapshotRepo.findFloorplanHistory(floorplanName, complexId, lookback).stream()
                .map(p -> new PriceHistoryDto(p.getScrapedAt(), p.getMinPrice(), p.getMaxPrice(),
                        p.getAvgPrice(), p.getUnitCount()))
                .toList();
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                "No history found for floor plan '" + floorplanName + "'.");
        return rows;
    }

    public List<RentedUnitDto> getRented(Integer complexId, int days) {
        String lookback = "-" + days + " days";
        return snapshotRepo.findRentedUnits(complexId, lookback).stream()
                .map(p -> new RentedUnitDto(p.getUnitId(), p.getFloorplanName(), p.getFloor(),
                        p.getBedrooms(), p.getLastPrice(), p.getLastAvailableDate(), p.getLastSeen()))
                .toList();
    }
}

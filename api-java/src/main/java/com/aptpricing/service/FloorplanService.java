package com.aptpricing.service;

import com.aptpricing.dto.FloorplanSummaryDto;
import com.aptpricing.dto.PriceDropDto;
import com.aptpricing.dto.UnitDto;
import com.aptpricing.repository.LeaseTermPriceRepository;
import com.aptpricing.repository.PriceSnapshotRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
public class FloorplanService {

    private final PriceSnapshotRepository snapshotRepo;
    private final LeaseTermPriceRepository leaseRepo;

    public FloorplanService(PriceSnapshotRepository snapshotRepo, LeaseTermPriceRepository leaseRepo) {
        this.snapshotRepo = snapshotRepo;
        this.leaseRepo = leaseRepo;
    }

    public List<Integer> getLeaseTerms(Integer complexId) {
        return leaseRepo.findDistinctLeaseMonths(complexId);
    }

    public List<FloorplanSummaryDto> getFloorplans(Integer complexId, Integer leaseTerm) {
        if (leaseTerm != null && leaseTerm != 15) {
            List<FloorplanSummaryDto> rows = leaseRepo.findFloorplanSummariesByTerm(complexId, leaseTerm)
                    .stream().map(this::toFloorplanSummaryDto).toList();
            if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                    "No lease term data for " + leaseTerm + " months. Run lease_terms.py first.");
            return rows;
        }
        return snapshotRepo.findFloorplanSummaries(complexId).stream()
                .map(this::toFloorplanSummaryDto).toList();
    }

    public List<UnitDto> getUnitsForFloorplan(String floorplanName, Integer complexId, Integer leaseTerm) {
        List<UnitDto> rows;
        if (leaseTerm != null && leaseTerm != 15) {
            rows = leaseRepo.findUnitsByFloorplanAndTerm(floorplanName, complexId, leaseTerm).stream()
                    .map(p -> new UnitDto(p.getComplexId(), p.getComplexName(), floorplanName, null,
                            p.getUnitId(), p.getFloor(), p.getBedrooms(), p.getBathrooms(), p.getSqft(),
                            p.getPrice(), p.getAvailableDate(), p.getAvailNote(),
                            p.getSpecialTags(), p.getUnitFeatures(), p.getScrapedAt()))
                    .toList();
            if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                    "No lease term data for " + leaseTerm + " months. Run lease_terms.py first.");
        } else {
            rows = snapshotRepo.findUnitsByFloorplan(floorplanName, complexId).stream()
                    .map(p -> new UnitDto(p.getComplexId(), p.getComplexName(), floorplanName, null,
                            p.getUnitId(), p.getFloor(), p.getBedrooms(), p.getBathrooms(), p.getSqft(),
                            p.getPrice(), p.getAvailableDate(), p.getAvailNote(),
                            p.getSpecialTags(), p.getUnitFeatures(), p.getScrapedAt()))
                    .toList();
        }
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                "Floor plan '" + floorplanName + "' not found.");
        return rows;
    }

    public List<PriceDropDto> getPriceDrops(Integer complexId, Integer leaseTerm) {
        if (leaseTerm != null && leaseTerm != 15) {
            return leaseRepo.findPriceDropsByTerm(complexId, leaseTerm).stream()
                    .map(this::toPriceDropDto).toList();
        }
        return snapshotRepo.findPriceDrops(complexId).stream()
                .map(this::toPriceDropDto).toList();
    }

    // ── mapping helpers ───────────────────────────────────────────────────────

    private FloorplanSummaryDto toFloorplanSummaryDto(PriceSnapshotRepository.FloorplanSummaryProjection p) {
        return new FloorplanSummaryDto(p.getComplexId(), p.getComplexName(), p.getFloorplanName(),
                p.getFloorplanSlug(), p.getBedrooms(), p.getBathrooms(), p.getSqft(),
                p.getAvailableUnits(), p.getMinPrice(), p.getMaxPrice(), p.getAvgPrice(),
                p.getEarliestAvailable(), p.getSpecialTags(), p.getScrapedAt(),
                p.getImageUrl(), p.getUrlFloor());
    }

    private FloorplanSummaryDto toFloorplanSummaryDto(LeaseTermPriceRepository.FloorplanSummaryProjection p) {
        return new FloorplanSummaryDto(p.getComplexId(), p.getComplexName(), p.getFloorplanName(),
                p.getFloorplanSlug(), p.getBedrooms(), p.getBathrooms(), p.getSqft(),
                p.getAvailableUnits(), p.getMinPrice(), p.getMaxPrice(), p.getAvgPrice(),
                p.getEarliestAvailable(), p.getSpecialTags(), p.getScrapedAt(),
                p.getImageUrl(), p.getUrlFloor());
    }

    private PriceDropDto toPriceDropDto(PriceSnapshotRepository.PriceDropProjection p) {
        return new PriceDropDto(p.getComplexId(), p.getFloorplanName(), p.getBestUnitId(),
                p.getCurrentMin(), p.getBaselineMin(), p.getCumulativeDrop(),
                p.getDropPct(), p.getDirection(), p.getFirstSeen());
    }

    private PriceDropDto toPriceDropDto(LeaseTermPriceRepository.PriceDropProjection p) {
        return new PriceDropDto(p.getComplexId(), p.getFloorplanName(), p.getBestUnitId(),
                p.getCurrentMin(), p.getBaselineMin(), p.getCumulativeDrop(),
                p.getDropPct(), p.getDirection(), p.getFirstSeen());
    }
}

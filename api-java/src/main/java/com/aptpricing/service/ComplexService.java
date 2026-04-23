package com.aptpricing.service;

import com.aptpricing.dto.ComplexDto;
import com.aptpricing.dto.ScrapeDto;
import com.aptpricing.repository.ComplexRepository;
import com.aptpricing.repository.PriceSnapshotRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ComplexService {

    private final ComplexRepository complexRepo;
    private final PriceSnapshotRepository snapshotRepo;

    public ComplexService(ComplexRepository complexRepo, PriceSnapshotRepository snapshotRepo) {
        this.complexRepo = complexRepo;
        this.snapshotRepo = snapshotRepo;
    }

    public List<ComplexDto> getComplexes() {
        return complexRepo.findAll().stream()
                .map(c -> new ComplexDto(c.getId(), c.getName(), c.getDisplayName(),
                        c.getCity(), c.getState(), c.getUrl()))
                .toList();
    }

    public List<ScrapeDto> getScrapes(Integer complexId) {
        return snapshotRepo.findScrapes(complexId).stream()
                .map(p -> new ScrapeDto(p.getScrapedAt(), p.getUnitCount()))
                .toList();
    }
}

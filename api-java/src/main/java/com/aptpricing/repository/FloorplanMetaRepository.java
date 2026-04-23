package com.aptpricing.repository;

import com.aptpricing.entity.FloorplanMeta;
import com.aptpricing.entity.FloorplanMetaId;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FloorplanMetaRepository extends JpaRepository<FloorplanMeta, FloorplanMetaId> {
    // All joins to floorplan_meta happen inside PriceSnapshotRepository / LeaseTermPriceRepository
    // native queries. This repository exists for potential standalone lookups.
}

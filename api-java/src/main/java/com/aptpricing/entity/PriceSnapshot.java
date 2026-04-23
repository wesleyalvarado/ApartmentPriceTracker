package com.aptpricing.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "price_snapshots")
@Getter
@NoArgsConstructor
public class PriceSnapshot {

    @Id
    private Integer id;

    @Column(name = "complex_id")
    private Integer complexId;

    @Column(name = "scraped_at")
    private String scrapedAt;

    @Column(name = "floorplan_name")
    private String floorplanName;

    @Column(name = "floorplan_slug")
    private String floorplanSlug;

    @Column(name = "unit_id")
    private String unitId;

    private Integer floor;
    private Double bedrooms;
    private Double bathrooms;
    private Integer sqft;
    private Integer price;

    @Column(name = "available_date")
    private String availableDate;

    @Column(name = "avail_note")
    private String availNote;

    @Column(name = "special_tags")
    private String specialTags;

    @Column(name = "unit_features")
    private String unitFeatures;
}

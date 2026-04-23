package com.aptpricing.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "floorplan_meta")
@Getter
@NoArgsConstructor
public class FloorplanMeta {

    @EmbeddedId
    private FloorplanMetaId id;

    @Column(name = "floorplan_slug")
    private String floorplanSlug;

    private Integer floor;
    private Double bedrooms;
    private Double bathrooms;
    private Integer sqft;

    @Column(name = "special_tags")
    private String specialTags;

    @Column(name = "image_url")
    private String imageUrl;
}

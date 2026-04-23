package com.aptpricing.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.EqualsAndHashCode;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Embeddable
@Getter
@NoArgsConstructor
@EqualsAndHashCode
public class FloorplanMetaId implements Serializable {

    @Column(name = "complex_id")
    private Integer complexId;

    @Column(name = "floorplan_name")
    private String floorplanName;
}

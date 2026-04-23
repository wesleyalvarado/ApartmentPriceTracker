package com.aptpricing.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "lease_term_prices")
@Getter
@NoArgsConstructor
public class LeaseTermPrice {

    @Id
    private Integer id;

    @Column(name = "complex_id")
    private Integer complexId;

    @Column(name = "scraped_at")
    private String scrapedAt;

    @Column(name = "unit_id")
    private String unitId;

    @Column(name = "floorplan_name")
    private String floorplanName;

    @Column(name = "move_in_date")
    private String moveInDate;

    @Column(name = "lease_months")
    private Integer leaseMonths;

    @Column(name = "monthly_rent")
    private Integer monthlyRent;
}

package com.aptpricing.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "complexes")
@Getter
@NoArgsConstructor
public class Complex {

    @Id
    private Integer id;

    private String name;

    @Column(name = "display_name")
    private String displayName;

    private String city;
    private String state;
    private String url;
}

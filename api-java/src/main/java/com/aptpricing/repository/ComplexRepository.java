package com.aptpricing.repository;

import com.aptpricing.entity.Complex;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ComplexRepository extends JpaRepository<Complex, Integer> {
    // findAll() inherited from JpaRepository — no custom queries needed
}

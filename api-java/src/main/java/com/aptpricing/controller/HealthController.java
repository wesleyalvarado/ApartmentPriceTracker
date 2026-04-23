package com.aptpricing.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Map;

@RestController
public class HealthController {

    @Value("${spring.datasource.url}")
    private String datasourceUrl;

    @GetMapping("/health")
    public Map<String, Object> health() {
        String dbPath = datasourceUrl.replace("jdbc:sqlite:", "");
        boolean dbExists = Files.exists(Path.of(dbPath));
        return Map.of(
                "status", dbExists ? "ok" : "db_missing",
                "db", dbPath,
                "db_exists", dbExists,
                "time", Instant.now().toString()
        );
    }
}

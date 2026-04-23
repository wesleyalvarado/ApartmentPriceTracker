package com.aptpricing.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.file.Path;

@Service
public class ScraperScheduler {

    private static final Logger log = LoggerFactory.getLogger(ScraperScheduler.class);

    @Value("${scraper.base-path}")
    private String scraperBasePath;

    // Runs daily at 8:00 AM — cron configurable via scraper.cron or SCRAPER_CRON env var
    @Scheduled(cron = "${scraper.cron}")
    public void runDailyScrape() {
        log.info("=== Daily scrape starting ===");
        run("camden_greenville", "scraper.py");
        run("camden_greenville", "lease_terms.py");
        run("skyhouse_dallas",   "scraper.py");
        run("skyhouse_dallas",   "lease_terms.py");
        log.info("=== Daily scrape complete ===");
    }

    private void run(String complex, String script) {
        Path workDir = Path.of(scraperBasePath, complex).toAbsolutePath();
        log.info("[scraper] {} / {}", complex, script);
        try {
            Process process = new ProcessBuilder("python3", script)
                    .directory(workDir.toFile())
                    .redirectErrorStream(true)
                    .start();

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream()))) {
                reader.lines().forEach(line -> log.info("[{}] {}", complex, line));
            }

            int exit = process.waitFor();
            if (exit != 0) {
                log.error("[scraper] {} / {} exited with code {}", complex, script, exit);
            }
        } catch (Exception e) {
            log.error("[scraper] Failed to run {} / {}: {}", complex, script, e.getMessage());
        }
    }
}

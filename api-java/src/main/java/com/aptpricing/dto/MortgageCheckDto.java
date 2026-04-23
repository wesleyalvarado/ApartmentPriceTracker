package com.aptpricing.dto;

public record MortgageCheckDto(
        long maxPurchasePrice,
        long downPaymentAmount,
        long loanAmount,
        long monthlyPi,
        long monthlyTax,
        long monthlyInsurance,
        long totalMonthly
) {}

# Memory: FIND-0004 — Hardcoded Database Password in DatabaseConfig

## Metadata
- **Category**: hardcoded_secret
- **Service**: payment-service
- **Severity**: medium
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044328+00:00

## Fix Approach
Replace hardcoded DB username and password in src/main/java/com/coupang/payment/config/DatabaseConfig.java with environment variables DB_USERNAME and DB_PASSWORD. Add fail-fast validation in the DataSource bean to throw IllegalStateException if either env var is missing. .env.example already contains DB_PASSWORD placeholder and .gitignore already contains .env.

## Files Modified
- `src/main/java/com/coupang/payment/config/DatabaseConfig.java`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 0

## PR
https://github.com/aaronkjin/coupang-payment-service/pull/24

## Error
No errors.

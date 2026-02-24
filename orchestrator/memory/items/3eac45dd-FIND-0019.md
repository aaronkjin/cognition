# Memory: FIND-0019 — Customer PII Exposed in Request Logging Middleware

## Metadata
- **Category**: pii_logging
- **Service**: catalog-service
- **Severity**: low
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044392+00:00

## Fix Approach
Created PII masking utility in src/utils/piiMasker.ts. Mask request body fields (name, email, phone, address, ssn, creditCard) before logging. Mask client IP. Updated src/middleware/logging.ts to sanitize request bodies and mask client IP before logging. Added tests to verify raw PII never appears in logs.

## Files Modified
- `src/utils/piiMasker.ts`
- `src/middleware/logging.ts`
- `tests/piiMasker.test.ts`
- `tests/piiLogging.test.ts`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 2

## PR
https://github.com/aaronkjin/coupang-catalog-service/pull/23

## Error
No errors.

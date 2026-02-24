# Memory: FIND-0001 — Remote Code Execution in Log4j Core

## Metadata
- **Category**: dependency_vulnerability
- **Service**: payment-service
- **Severity**: critical
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.043308+00:00

## Fix Approach
Upgrade log4j-core from 2.14.1 to 2.17.1 in pom.xml. This is a minor/security version bump with no breaking API changes; codebase uses SLF4J so no application code changes were required beyond the version bump.

## Files Modified
- `pom.xml`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 0

## PR
https://github.com/aaronkjin/coupang-payment-service/pull/22

## Error
No errors.

# Memory: FIND-0015 — Prototype Pollution in Lodash

## Metadata
- **Category**: dependency_vulnerability
- **Service**: catalog-service
- **Severity**: critical
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044310+00:00

## Fix Approach
Patch version bump from 4.17.20 to 4.17.21. This is a security-only patch fixing prototype pollution in _.merge and _.zipObjectDeep. No breaking API changes.

## Files Modified
- `package.json`
- `package-lock.json`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 0

## PR
https://github.com/aaronkjin/coupang-catalog-service/pull/19

## Error
No errors.

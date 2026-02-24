# Memory: FIND-0016 — Reflected XSS in Product Search Response

## Metadata
- **Category**: xss
- **Service**: catalog-service
- **Severity**: high
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044350+00:00

## Fix Approach
Add an HTML-escaping helper (src/utils/sanitize.ts) and escape user-supplied query before embedding in HTML response. Applied escapeHtml to the search query in src/controllers/catalogController.ts to prevent reflected XSS while preserving visible text.

## Files Modified
- `src/utils/sanitize.ts`
- `src/controllers/catalogController.ts`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 0

## PR
https://github.com/aaronkjin/coupang-catalog-service/pull/20

## Error
No errors.

# Memory: FIND-0017 — Path Traversal in File Download Endpoint

## Metadata
- **Category**: path_traversal
- **Service**: catalog-service
- **Severity**: medium
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044372+00:00

## Fix Approach
Sanitize user-supplied filename in all file endpoints (downloadFile, uploadFile, deleteFile) by resolving the full path and verifying it stays within UPLOAD_DIR. Use path.resolve() and startsWith() check to prevent directory traversal via ../ sequences.

## Files Modified
- `src/controllers/fileController.ts`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 0

## PR
https://github.com/aaronkjin/coupang-catalog-service/pull/21

## Error
No errors.

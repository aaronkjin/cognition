# Memory: FIND-0009 — SSRF Vulnerability in Requests Library

## Metadata
- **Category**: dependency_vulnerability
- **Service**: user-service
- **Severity**: high
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044319+00:00

## Fix Approach
Update requests in requirements.txt from 2.25.0 to 2.31.0, run pip install -r requirements.txt, verify with pip check, run pytest tests/ -v. No direct usages of requests found in repo; no code changes required.

## Files Modified
- `requirements.txt`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 0

## PR
https://github.com/aaronkjin/coupang-user-service/pull/22

## Error
No errors.

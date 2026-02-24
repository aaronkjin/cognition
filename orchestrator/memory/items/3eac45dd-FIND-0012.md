# Memory: FIND-0012 — Hardcoded JWT Secret Key in Configuration

## Metadata
- **Category**: hardcoded_secret
- **Service**: user-service
- **Severity**: medium
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044357+00:00

## Fix Approach
Replace hardcoded JWT_SECRET in config.py (line 15) with os.environ["JWT_SECRET"]; add fail-fast RuntimeError if missing or empty; set JWT_SECRET for tests via tests/conftest.py using a test-only placeholder. .env.example already contained a JWT_SECRET placeholder and .gitignore already lists .env. Files changed: config.py, tests/conftest.py.

## Files Modified
- `/home/ubuntu/coupang-user-service/config.py`
- `/home/ubuntu/coupang-user-service/tests/conftest.py`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 0

## PR
https://github.com/aaronkjin/coupang-user-service/pull/24

## Error
No errors.

# Memory: FIND-0008 — SQL Injection in User Search Endpoint

## Metadata
- **Category**: sql_injection
- **Service**: user-service
- **Severity**: critical
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044269+00:00

## Fix Approach
Replace f-string interpolation in search_users (line 55) with parameterized query using SQLite ? placeholder. The LIKE pattern is passed as a parameter value.

## Files Modified
- `app/routes/user_routes.py`
- `tests/test_users.py`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 3

## PR
https://github.com/aaronkjin/coupang-user-service/pull/23

## Error
No errors.

# Memory: FIND-0014 — Unencrypted Password Reset Tokens

## Metadata
- **Category**: missing_encryption
- **Service**: user-service
- **Severity**: high
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044343+00:00

## Fix Approach
Hash password reset tokens using SHA-256 (hashlib.sha256) before storage. Tokens only need equality checks, not retrieval, so one-way hashing is appropriate. Added app/utils/crypto.py with hash_token and verify_token (constant-time compare) and updated app/models/user.py to call hash_token in set_reset_token and added verify_reset_token.

## Files Modified
- `app/utils/crypto.py`
- `app/models/user.py`
- `tests/test_reset_token_hashing.py`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 10

## PR
https://github.com/aaronkjin/coupang-user-service/pull/26

## Error
No errors.

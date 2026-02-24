# Memory: FIND-0010 — PII Logged in User Registration Flow

## Metadata
- **Category**: pii_logging
- **Service**: user-service
- **Severity**: high
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044335+00:00

## Fix Approach
Create PII masking utility at app/utils/pii_masker.py with mask_email, mask_phone, mask_credit_card, mask_name. Update logger call in app/routes/user_routes.py (line 112) to use masked values. Add tests verifying raw email and phone do not appear in logs and masked versions do.

## Files Modified
- `app/utils/pii_masker.py`
- `app/routes/user_routes.py`
- `tests/test_pii_masking.py`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 10

## PR
https://github.com/aaronkjin/coupang-user-service/pull/25

## Error
No errors.

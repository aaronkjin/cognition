# Memory: FIND-0002 — SQL Injection in TransactionDAO.findByUserId

## Metadata
- **Category**: sql_injection
- **Service**: payment-service
- **Severity**: high
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044299+00:00

## Fix Approach
Replace raw Statement concatenation with JDBC PreparedStatement parameterized queries. Updated findByUserId to use 'SELECT * FROM transactions WHERE user_id = ?' and findById to use 'SELECT * FROM transactions WHERE id = ?'. Added H2-based integration tests that pass SQL injection payloads to verify they are treated as data.

## Files Modified
- `src/main/java/com/coupang/payment/dao/TransactionDAO.java`
- `src/test/java/com/coupang/payment/dao/TransactionDAOTest.java`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 8

## PR
https://github.com/aaronkjin/coupang-payment-service/pull/23

## Error
No errors.

# Memory: FIND-0006 — Unencrypted PAN Storage in Transaction Entity

## Metadata
- **Category**: missing_encryption
- **Service**: payment-service
- **Severity**: medium
- **Outcome**: SUCCESS
- **Confidence**: high
- **Data Source**: live
- **Run ID**: 3eac45dd
- **Created**: 2026-02-24T07:05:19.044364+00:00

## Fix Approach
AES-256-GCM encryption for PAN data using javax.crypto.Cipher. Encrypt card numbers in PaymentService before storage using EncryptionUtil.encrypt(), store Base64(IV||ciphertext||tag) in DB; decrypt on read in TransactionDAO using EncryptionUtil.decrypt(). Encryption key comes from PAN_ENCRYPTION_KEY env var (64-char hex -> 32 bytes). Startup validation via EncryptionConfig calling EncryptionUtil.init().

## Files Modified
- `src/main/java/com/coupang/payment/security/EncryptionUtil.java`
- `src/main/java/com/coupang/payment/config/EncryptionConfig.java`
- `src/main/java/com/coupang/payment/service/PaymentService.java`
- `src/main/java/com/coupang/payment/dao/TransactionDAO.java`
- `src/main/java/com/coupang/payment/model/Transaction.java`
- `.env.example`
- `src/test/java/com/coupang/payment/security/EncryptionUtilTest.java`
- `src/test/java/com/coupang/payment/service/PaymentServiceTest.java`

## Test Results
- **Tests Passed**: Yes
- **Tests Added**: 10

## PR
https://github.com/aaronkjin/coupang-payment-service/pull/26

## Error
No errors.

# Missing Encryption Remediation

## Overview
Add encryption to sensitive data that is currently stored or transmitted in plaintext. Apply the appropriate encryption strategy (hashing for passwords, AES-256 for retrievable data) and verify the fix with tests.

## What's Needed From User
The session prompt will include:
- `finding_id` — unique identifier for this finding (e.g., FIND-0012)
- `file_path` — path to the source file where plaintext sensitive data is handled
- `line_number` — line number where the issue is located
- `language` — Java, Python, TypeScript, or Go
- `repo_url` — the repository URL to clone
- `service_name` — the service this file belongs to
- `cwe_id` — CWE-311 (Missing Encryption of Sensitive Data) or CWE-256 (Plaintext Storage of a Password)
- `title` — short description of the vulnerability
- `description` — detailed description of what sensitive data is unencrypted

## Procedure
1. Clone the repository from `repo_url` if not already present.
2. Read the finding details from the session prompt.
3. Update structured output: status="analyzing", progress_pct=10, current_step="Reading finding details".
4. Open the file at `file_path` and navigate to `line_number`.
5. Identify the sensitive data type and determine the correct encryption approach:

   **Passwords** → One-way hashing (NOT reversible encryption):
   - Java: `BCryptPasswordEncoder` (Spring Security) or `BCrypt.hashpw()` (jBCrypt)
   - Python: `bcrypt.hashpw()` or `passlib.hash.bcrypt`
   - TypeScript: `bcrypt.hash()` / `bcrypt.compare()`
   - Go: `golang.org/x/crypto/bcrypt`

   **Credit card numbers / PAN data** → AES-256 encryption (reversible, for retrieval):
   - Java: `javax.crypto.Cipher` with AES/GCM/NoPadding, or JPA `@Convert` with a custom `AttributeConverter`
   - Python: `cryptography.fernet.Fernet` or `sqlalchemy_utils.EncryptedType`
   - TypeScript: `crypto.createCipheriv('aes-256-gcm', ...)`
   - Go: `crypto/aes` with GCM mode

   **Tokens / reset codes** → SHA-256 hash (if only equality checks needed) or AES-256 (if retrieval needed):
   - Java: `MessageDigest.getInstance("SHA-256")`
   - Python: `hashlib.sha256()`
   - TypeScript: `crypto.createHash('sha256')`
   - Go: `crypto/sha256`

   **Other sensitive data** (SSN, etc.) → AES-256 encryption.

6. Check if the project already has an encryption utility, security module, or established pattern for handling sensitive data. If so, follow the existing pattern.
7. Update structured output: status="analyzing", progress_pct=20, fix_approach=<plan describing encryption approach, data type, and method>, confidence=<assessment>.
8. Create a new branch named `fix/FIND-{finding_id}-encryption` from the default branch.
9. Implement the encryption based on the data type:

   **Password hashing (Python example):**
   ```python
   import bcrypt

   # BEFORE — storing plaintext
   user.password = plain_password

   # AFTER — storing hashed
   user.password = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()

   # For comparison:
   def verify_password(plain: str, hashed: str) -> bool:
       return bcrypt.checkpw(plain.encode(), hashed.encode())
   ```

   **Password hashing (Java/Spring example):**
   ```java
   // BEFORE
   user.setPassword(plainPassword);

   // AFTER
   BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
   user.setPassword(encoder.encode(plainPassword));

   // For comparison:
   encoder.matches(plainPassword, user.getPassword());
   ```

   **AES-256 encryption (Python/Fernet example):**
   ```python
   from cryptography.fernet import Fernet
   import os

   ENCRYPTION_KEY = os.environ["DATA_ENCRYPTION_KEY"]
   fernet = Fernet(ENCRYPTION_KEY)

   # Encrypt
   encrypted = fernet.encrypt(plaintext.encode()).decode()

   # Decrypt
   decrypted = fernet.decrypt(encrypted.encode()).decode()
   ```

   **AES-256 encryption (TypeScript example):**
   ```typescript
   import crypto from 'crypto';

   const ENCRYPTION_KEY = process.env.DATA_ENCRYPTION_KEY!; // 32 bytes
   const IV_LENGTH = 12; // GCM standard

   function encrypt(text: string): string {
       const iv = crypto.randomBytes(IV_LENGTH);
       const cipher = crypto.createCipheriv('aes-256-gcm', Buffer.from(ENCRYPTION_KEY, 'hex'), iv);
       const encrypted = Buffer.concat([cipher.update(text, 'utf8'), cipher.final()]);
       const tag = cipher.getAuthTag();
       return Buffer.concat([iv, tag, encrypted]).toString('base64');
   }
   ```

10. Ensure encryption keys come from environment variables, NOT hardcoded in source:
    - Add the key env var to `.env.example` with a placeholder: `DATA_ENCRYPTION_KEY=generate-a-32-byte-key-here`
    - Add startup validation that fails if the key is missing.
11. Update structured output: status="fixing", progress_pct=50, files_modified=<list of modified files>.
12. If the data is stored in a database column, add a comment noting that existing plaintext data will need a data migration:
    ```python
    # NOTE: Existing plaintext data in the 'password' column needs a one-time migration
    # to bcrypt hashes. This migration is out of scope for this PR.
    ```
13. If applicable, check if the column type/size needs to change (e.g., bcrypt hashes are 60 chars, AES+base64 output is longer than plaintext). Note this in the PR body if a schema migration is needed.
14. Update structured output: status="fixing", progress_pct=60, files_modified=<updated list>.
15. Add tests:

    **For password hashing:**
    ```python
    def test_password_is_hashed():
        plain = "my-password-123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True
        assert verify_password("wrong-password", hashed) is False
    ```

    **For AES encryption:**
    ```python
    def test_encrypt_decrypt_roundtrip():
        original = "4111-1111-1111-1234"
        encrypted = encrypt(original)
        assert encrypted != original
        assert decrypt(encrypted) == original
    ```

16. Update structured output: status="testing", progress_pct=70, tests_added=<count>.
17. Run the full test suite.
18. If tests fail, fix the issues and re-run.
19. Update structured output: status="testing", progress_pct=75, tests_passed=<true/false>, tests_added=<count>.
20. Commit all changes with message: `fix: add encryption for sensitive data [{finding_id}]`.
21. Push the branch to the remote.
22. Update structured output: status="creating_pr", progress_pct=90.
23. Create a pull request with:
    - Title: `fix: add encryption for sensitive data [{finding_id}]`
    - Body that includes:
      - Reference to the CWE (CWE-311 or CWE-256)
      - What sensitive data type was unencrypted
      - Encryption approach chosen and why (hashing vs. symmetric encryption)
      - Environment variable(s) introduced for encryption keys
      - Note about data migration needed for existing plaintext data (if applicable)
      - Column type/size changes needed (if applicable)
      - Tests added
24. Update structured output: status="completed", progress_pct=100, pr_url=<the PR URL>.

## Specifications
When the task is complete, ALL of the following must be true:
- Sensitive data is no longer stored or transmitted in plaintext.
- Passwords use one-way hashing (bcrypt or argon2), NOT reversible encryption.
- Retrievable sensitive data uses AES-256 (GCM mode preferred) or Fernet encryption.
- Encryption keys come from environment variables, not hardcoded in source.
- Startup validation fails fast if required encryption key env vars are missing.
- Tests verify that stored/transmitted data is not plaintext.
- Tests verify that decryption (if applicable) recovers the original value.
- Tests verify that password comparison works (for hashed passwords).
- A comment notes the need for data migration of existing plaintext data (if applicable).
- All existing tests pass.
- A pull request exists on a feature branch (not main/master).
- Structured output reflects status="completed" with progress_pct=100.

## Structured Output Updates
Update the structured output JSON after each major step using this schema:
```json
{
  "finding_id": "<string>",
  "status": "analyzing | fixing | testing | creating_pr | completed | failed",
  "progress_pct": "<integer 0-100>",
  "current_step": "<string>",
  "fix_approach": "<string or null>",
  "files_modified": ["<array of strings>"],
  "tests_passed": "<boolean or null>",
  "tests_added": "<integer>",
  "pr_url": "<string or null>",
  "error_message": "<string or null>",
  "confidence": "high | medium | low"
}
```

Update at these checkpoints:
- After reading finding details: status="analyzing", progress_pct=10
- After determining encryption approach: status="analyzing", progress_pct=20, fix_approach=<plan>, confidence=<assessment>
- After implementing encryption: status="fixing", progress_pct=50, files_modified=<list>
- After adding migration comments and env var setup: status="fixing", progress_pct=60, files_modified=<updated list>
- After adding tests: status="testing", progress_pct=70, tests_added=<count>
- After running test suite: status="testing", progress_pct=75, tests_passed=<bool>
- After creating PR: status="creating_pr", progress_pct=90, pr_url=<url>
- On completion: status="completed", progress_pct=100
- On failure at any step: status="failed", error_message=<what went wrong>

## Advice and Pointers
- For passwords, ALWAYS use one-way hashing (bcrypt, argon2), NEVER reversible encryption. If someone asks "can we decrypt the password later?", the answer is no — that is the point.
- For data that needs to be retrieved (credit cards, SSNs), use authenticated encryption: AES-GCM or Fernet. These provide both confidentiality and integrity.
- Check if the project already has an encryption utility or security module. Reuse existing patterns rather than introducing a new approach.
- Bcrypt hashes are 60 characters long. AES-256-GCM + base64 output is roughly 1.5x the input length plus ~44 bytes of overhead (IV + auth tag). Ensure database columns are large enough.
- For Fernet (Python), the key must be 32 bytes URL-safe base64 encoded. Generate with `Fernet.generate_key()`.
- For AES-256-GCM, always use a random IV (nonce) for each encryption operation. Never reuse IVs with the same key.
- Do NOT implement a data migration for existing plaintext data — that is out of scope. Just add the comment noting it is needed.
- If the project uses an ORM, check for built-in encryption support (e.g., JPA `@Convert`, SQLAlchemy `TypeDecorator`) to keep the encryption transparent to business logic.

## Forbidden Actions
- Do not commit directly to main or master branch. Always create a new feature branch.
- Do not disable, skip, or delete existing tests.
- Do not modify unrelated business logic.
- Do not introduce new dependencies without strong justification.
- Do not remove or weaken existing security controls.
- Do not use reversible encryption for passwords — always use hashing.
- Do not use ECB mode for AES encryption — use GCM or CBC with HMAC.
- Do not hardcode encryption keys in source code.
- Do not use MD5 or SHA-1 for password hashing — these are too fast and vulnerable to brute force.
- Do not implement a data migration for existing records — note it as needed but leave it out of scope.

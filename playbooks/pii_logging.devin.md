# PII Logging Remediation

## Overview
Remove or mask Personally Identifiable Information (PII) from log statements to prevent sensitive data exposure in application logs. Create reusable masking utilities, update all affected log lines, and add tests verifying that raw PII never appears in log output.

## What's Needed From User
The session prompt will include:
- `finding_id` — unique identifier for this finding (e.g., FIND-0008)
- `file_path` — path to the source file containing the PII logging issue
- `line_number` — line number where PII is logged
- `language` — Java, Python, TypeScript, or Go
- `repo_url` — the repository URL to clone
- `service_name` — the service this file belongs to
- `cwe_id` — CWE-532 (Insertion of Sensitive Information into Log File)
- `title` — short description of the vulnerability
- `description` — detailed description of what PII is being logged

## Procedure
1. Clone the repository from `repo_url` if not already present.
2. Read the finding details from the session prompt.
3. Update structured output: status="analyzing", progress_pct=10, current_step="Reading finding details".
4. Open the file at `file_path` and navigate to `line_number`.
5. Identify what PII is being logged and how:
   - Direct logging: `logger.info(f"User email: {user.email}")`
   - Object logging: `logger.info(f"User: {user}")` where `user` contains PII fields
   - Request/response logging: `logger.debug(f"Request body: {request.body}")` containing PII
   - Error logging: `logger.error(f"Failed for user {user_data}")` with full user data
6. Scan ALL log statements in the entire file (and closely related files in the same module/package) for other instances of PII logging. Common PII types to look for:
   - Email addresses
   - Phone numbers
   - Social Security Numbers (SSNs)
   - Credit card numbers / PANs
   - Full names (first + last)
   - Physical addresses
   - Dates of birth
   - IP addresses (in some contexts)
7. Update structured output: status="analyzing", progress_pct=20, fix_approach=<plan listing all PII logging locations found and masking strategy>, confidence=<assessment>.
8. Create a new branch named `fix/FIND-{finding_id}-pii-logging` from the default branch.
9. Check if the project already has a PII masking utility. If it does, use it. If not, create one in a shared/utility location appropriate for the project structure.
10. Implement masking functions with these rules:

    **Email**: `user@example.com` → `u***@example.com` (show first character + domain)
    **Phone**: `555-123-4567` → `***-***-4567` (show last 4 digits)
    **Credit card**: `4111-1111-1111-1234` → `****-****-****-1234` (show last 4 digits)
    **SSN**: `123-45-6789` → `***-**-6789` (show last 4 digits)
    **Name**: `John Doe` → `J*** D***` (show first character of each part)
    **Other PII**: Replace with `[REDACTED]`

    **Python example:**
    ```python
    import re

    def mask_email(email: str) -> str:
        if not email or "@" not in email:
            return "[REDACTED]"
        local, domain = email.split("@", 1)
        return f"{local[0]}***@{domain}"

    def mask_phone(phone: str) -> str:
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 4:
            return "[REDACTED]"
        return f"***-***-{digits[-4:]}"

    def mask_credit_card(card: str) -> str:
        digits = re.sub(r'\D', '', card)
        if len(digits) < 4:
            return "[REDACTED]"
        return f"****-****-****-{digits[-4:]}"

    def mask_name(name: str) -> str:
        parts = name.strip().split()
        return " ".join(f"{p[0]}***" for p in parts if p)
    ```

    **Java example:**
    ```java
    public class PiiMasker {
        public static String maskEmail(String email) {
            if (email == null || !email.contains("@")) return "[REDACTED]";
            String[] parts = email.split("@", 2);
            return parts[0].charAt(0) + "***@" + parts[1];
        }

        public static String maskPhone(String phone) {
            String digits = phone.replaceAll("\\D", "");
            if (digits.length() < 4) return "[REDACTED]";
            return "***-***-" + digits.substring(digits.length() - 4);
        }
    }
    ```

    **TypeScript example:**
    ```typescript
    export function maskEmail(email: string): string {
        if (!email || !email.includes('@')) return '[REDACTED]';
        const [local, domain] = email.split('@');
        return `${local[0]}***@${domain}`;
    }

    export function maskPhone(phone: string): string {
        const digits = phone.replace(/\D/g, '');
        if (digits.length < 4) return '[REDACTED]';
        return `***-***-${digits.slice(-4)}`;
    }
    ```

11. Update the log statements to use the masking functions:

    **Direct PII logging:**
    ```python
    # BEFORE
    logger.info(f"User email: {user.email}")
    # AFTER
    logger.info(f"User email: {mask_email(user.email)}")
    ```

    **Object/dict logging with PII fields:**
    ```python
    # BEFORE
    logger.info(f"User data: {user_dict}")
    # AFTER — Option A: log only non-PII fields
    safe_fields = {k: v for k, v in user_dict.items() if k not in ("email", "phone", "ssn")}
    logger.info(f"User data: {safe_fields}")

    # AFTER — Option B: create sanitized copy
    sanitized = {**user_dict, "email": mask_email(user_dict.get("email", "")), "phone": mask_phone(user_dict.get("phone", ""))}
    logger.info(f"User data: {sanitized}")
    ```

12. Update structured output: status="fixing", progress_pct=50, files_modified=<list of modified files>.
13. Add tests that verify PII is properly masked in log output:

    **Python example (using caplog or similar):**
    ```python
    def test_pii_not_logged(caplog):
        email = "john.doe@example.com"
        phone = "555-123-4567"
        # Call the function that triggers the log statement
        process_user({"email": email, "phone": phone})
        # Verify raw PII does NOT appear in logs
        assert email not in caplog.text
        assert phone not in caplog.text
        # Verify masked versions DO appear
        assert "j***@example.com" in caplog.text
        assert "***-***-4567" in caplog.text
    ```

    **Java example (using LogCaptor or similar):**
    ```java
    @Test
    void testPiiNotLogged() {
        LogCaptor logCaptor = LogCaptor.forClass(UserService.class);
        userService.processUser("john@example.com", "555-123-4567");
        assertThat(logCaptor.getInfoLogs())
            .noneMatch(log -> log.contains("john@example.com"))
            .anyMatch(log -> log.contains("j***@example.com"));
    }
    ```

14. Update structured output: status="testing", progress_pct=65, tests_added=<count>.
15. Run the full test suite.
16. If tests fail, fix the issues and re-run.
17. Update structured output: status="testing", progress_pct=75, tests_passed=<true/false>, tests_added=<count>.
18. Commit all changes with message: `fix: mask PII in log output [{finding_id}]`.
19. Push the branch to the remote.
20. Update structured output: status="creating_pr", progress_pct=90.
21. Create a pull request with:
    - Title: `fix: mask PII in log output [{finding_id}]`
    - Body that includes:
      - Reference to CWE-532 (Sensitive Information in Log File)
      - Types of PII that were being logged
      - Masking strategy applied
      - List of log statements fixed
      - Tests added to verify masking
22. Update structured output: status="completed", progress_pct=100, pr_url=<the PR URL>.

## Specifications
When the task is complete, ALL of the following must be true:
- No raw PII values (emails, phones, SSNs, credit cards, full names) appear in any log statement in the modified file(s).
- PII values are masked using the specified masking rules (partial visibility, not full redaction, where appropriate).
- A reusable masking utility exists (or the project's existing one was used).
- At least one test verifies that raw PII does NOT appear in log output and that masked values DO appear.
- All existing tests pass.
- A pull request exists on a feature branch (not main/master) with a clear title and body.
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
- After scanning for all PII logging locations: status="analyzing", progress_pct=20, fix_approach=<plan>, confidence=<assessment>
- After implementing masking and updating log statements: status="fixing", progress_pct=50, files_modified=<list>
- After adding tests: status="testing", progress_pct=65, tests_added=<count>
- After running test suite: status="testing", progress_pct=75, tests_passed=<bool>
- After creating PR: status="creating_pr", progress_pct=90, pr_url=<url>
- On completion: status="completed", progress_pct=100
- On failure at any step: status="failed", error_message=<what went wrong>

## Advice and Pointers
- Search for ALL log statements in the file, not just the reported one. PII logging often happens in multiple places within the same service.
- Look for logging of entire request/response bodies, user objects, and error stack traces that might contain PII embedded in the message.
- If the project uses a logging framework with formatters/appenders (e.g., Logback patterns, Python logging formatters), consider whether a log filter/formatter-level solution is more appropriate than changing every log call.
- Be careful with `toString()` or `__str__`/`__repr__` methods on model objects — these often include all fields. Consider overriding them to exclude PII, or log specific fields instead of the whole object.
- Watch for PII in exception messages: `throw new Error("Invalid email: " + email)` — the exception message may end up in logs.
- If the project uses structured logging (JSON logs), make sure PII fields in the structured data are also masked, not just the message string.

## Forbidden Actions
- Do not commit directly to main or master branch. Always create a new feature branch.
- Do not disable, skip, or delete existing tests.
- Do not modify unrelated business logic.
- Do not introduce new dependencies without strong justification.
- Do not remove or weaken existing security controls.
- Do not remove log statements entirely unless they serve no purpose beyond logging PII. Prefer masking over removal — the log statement may be useful for debugging.
- Do not log the PII in a different location or at a different log level as a "fix".
- Do not use full redaction (`[REDACTED]`) when partial masking (showing last 4 digits, first character) is possible — partial visibility aids debugging.

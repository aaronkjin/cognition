# Hardcoded Secrets Remediation

## Overview
Externalize hardcoded secrets (passwords, API keys, tokens, connection strings) from source code to environment variables, add startup validation to fail fast on missing secrets, and ensure secret files are gitignored.

## What's Needed From User
The session prompt will include:
- `finding_id` — unique identifier for this finding (e.g., FIND-0003)
- `file_path` — path to the source file containing the hardcoded secret
- `line_number` — line number where the secret is located
- `language` — Java, Python, TypeScript, or Go
- `repo_url` — the repository URL to clone
- `service_name` — the service this file belongs to
- `cwe_id` — CWE-798 (Use of Hard-coded Credentials)
- `title` — short description of the vulnerability
- `description` — detailed description of what was found

## Procedure
1. Clone the repository from `repo_url` if not already present.
2. Read the finding details from the session prompt.
3. Update structured output: status="analyzing", progress_pct=10, current_step="Reading finding details".
4. Open the file at `file_path` and navigate to `line_number`.
5. Identify the hardcoded secret:
   - Database passwords: `password = "hunter2"`, `db_pass = "secret123"`
   - API keys: `api_key = "sk-abc123..."`, `STRIPE_KEY = "pk_live_..."`
   - Tokens: `jwt_secret = "mysecretkey"`, `auth_token = "Bearer abc..."`
   - Connection strings: `jdbc:mysql://user:pass@host/db`, `mongodb://user:pass@host`
6. Determine an appropriate environment variable name following these conventions:
   - Use UPPER_SNAKE_CASE.
   - Be descriptive: `DB_PASSWORD`, `JWT_SECRET`, `STRIPE_API_KEY`, `REDIS_AUTH_TOKEN`.
   - If the project already has a naming convention for env vars, follow that convention.
7. Search the entire codebase for other references to the same hardcoded value or related secrets in the same file/module. Note all locations.
8. Check if the project has an existing config/settings module that centralizes environment variable reading (e.g., `config.py`, `application.properties`, `config.ts`, `.env` loading). If it does, use that existing pattern.
9. Update structured output: status="analyzing", progress_pct=20, fix_approach=<plan describing env var name, all locations to change, and config pattern to follow>, confidence=<assessment>.
10. Create a new branch named `fix/FIND-{finding_id}-hardcoded-secret` from the default branch.
11. Replace the hardcoded secret with an environment variable read:

    **Java (plain):**
    ```java
    // BEFORE
    String dbPassword = "hunter2";
    // AFTER
    String dbPassword = System.getenv("DB_PASSWORD");
    ```

    **Java (Spring):**
    ```java
    // BEFORE
    private String dbPassword = "hunter2";
    // AFTER
    @Value("${DB_PASSWORD}")
    private String dbPassword;
    ```

    **Python:**
    ```python
    # BEFORE
    db_password = "hunter2"
    # AFTER
    import os
    db_password = os.environ["DB_PASSWORD"]
    ```

    **TypeScript/JavaScript:**
    ```typescript
    // BEFORE
    const dbPassword = "hunter2";
    // AFTER
    const dbPassword = process.env.DB_PASSWORD;
    ```

    **Go:**
    ```go
    // BEFORE
    dbPassword := "hunter2"
    // AFTER
    dbPassword := os.Getenv("DB_PASSWORD")
    ```

12. Add fail-fast validation at application startup. If the required env var is missing or empty, the application must fail with a clear error message:

    **Python:**
    ```python
    if not os.environ.get("DB_PASSWORD"):
        raise RuntimeError("Required environment variable DB_PASSWORD is not set")
    ```

    **Java:**
    ```java
    String dbPassword = System.getenv("DB_PASSWORD");
    if (dbPassword == null || dbPassword.isEmpty()) {
        throw new IllegalStateException("Required environment variable DB_PASSWORD is not set");
    }
    ```

    **TypeScript:**
    ```typescript
    if (!process.env.DB_PASSWORD) {
        throw new Error("Required environment variable DB_PASSWORD is not set");
    }
    ```

13. Update structured output: status="fixing", progress_pct=50, files_modified=<list of modified files>.
14. If a `.env.example`, `env.example`, or similar template file exists, add the new variable with a placeholder value:
    ```
    DB_PASSWORD=your-database-password-here
    ```
15. Check if `.env` is listed in `.gitignore`. If not, add `.env` to `.gitignore`.
16. Replace ALL other references to the same hardcoded value in the codebase (found in step 7).
17. Update structured output: status="fixing", progress_pct=60, files_modified=<updated list>.
18. Run the existing test suite:
    - Set the environment variable in the test environment or mock it as needed.
    - Java: `mvn test` or `gradle test`
    - Python: `pytest` or `python -m pytest`
    - TypeScript: `npm test`
    - Go: `go test ./...`
19. If tests fail because they depended on the hardcoded value, update the test configuration to set the env var in the test setup (e.g., test fixtures, conftest.py, beforeAll blocks).
20. Update structured output: status="testing", progress_pct=75, tests_passed=<true/false>, tests_added=0.
21. Commit all changes with message: `fix: externalize hardcoded secret to environment variable [{finding_id}]`.
22. Push the branch to the remote.
23. Update structured output: status="creating_pr", progress_pct=90.
24. Create a pull request with:
    - Title: `fix: externalize hardcoded secret to env var [{finding_id}]`
    - Body that includes:
      - Reference to CWE-798 (Use of Hard-coded Credentials)
      - What type of secret was hardcoded (password, API key, etc.) — do NOT include the actual secret value
      - The environment variable name introduced
      - Startup validation behavior
      - Instructions for setting the env var in deployment
25. Update structured output: status="completed", progress_pct=100, pr_url=<the PR URL>.

## Specifications
When the task is complete, ALL of the following must be true:
- No hardcoded secret values remain in the source code at the identified location or any duplicates found.
- The secret is read from an environment variable at runtime.
- A fail-fast validation exists that raises/throws an error at startup if the env var is missing.
- `.env` is listed in `.gitignore`.
- If `.env.example` exists, it contains the new variable with a placeholder.
- All existing tests pass.
- A pull request exists on a feature branch (not main/master) with a clear title and body. The PR body does NOT contain the actual secret value.
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
- After identifying all secret locations and config pattern: status="analyzing", progress_pct=20, fix_approach=<plan>, confidence=<assessment>
- After replacing secret with env var and adding validation: status="fixing", progress_pct=50, files_modified=<list>
- After updating .env.example and .gitignore: status="fixing", progress_pct=60, files_modified=<updated list>
- After running tests: status="testing", progress_pct=75, tests_passed=<bool>
- After creating PR: status="creating_pr", progress_pct=90, pr_url=<url>
- On completion: status="completed", progress_pct=100
- On failure at any step: status="failed", error_message=<what went wrong>

## Advice and Pointers
- Never log the actual secret value, even in error messages. Use messages like `"DB_PASSWORD is not set"` — never `"DB_PASSWORD=hunter2 is invalid"`.
- Check if the application already has a config/settings module that centralizes env var reading. If it does, add the new variable there rather than reading `os.environ` directly in the business logic file.
- For Java Spring applications, prefer `@Value("${VAR}")` or `@ConfigurationProperties` over raw `System.getenv()`.
- For Python projects using pydantic-settings, add the field to the existing Settings class.
- Some secrets may be in configuration files (application.yml, config.json) rather than source code — handle these the same way by replacing the value with an env var reference (e.g., `${DB_PASSWORD}` in Spring YAML).
- Search for the literal secret value across the ENTIRE repository. Hardcoded secrets are often copy-pasted into multiple files.
- If the secret is used in a test file as a test fixture, replace it with a clearly fake value (e.g., `test-secret-do-not-use-in-production`) and note that it is a test-only value.

## Forbidden Actions
- Do not commit directly to main or master branch. Always create a new feature branch.
- Do not disable, skip, or delete existing tests.
- Do not modify unrelated business logic.
- Do not introduce new dependencies without strong justification.
- Do not remove or weaken existing security controls.
- Do not include the actual secret value in the commit message, PR body, or any log output.
- Do not set a default value for the secret in code (the env var must be explicitly set in the environment).
- Do not store the secret in a file that gets committed to the repository.

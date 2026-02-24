# SQL Injection Remediation

## Overview
Replace string concatenation or interpolation in SQL queries with parameterized queries (prepared statements) to eliminate SQL injection vulnerabilities, add tests verifying injection payloads are safely handled, and open a pull request.

## What's Needed From User
The session prompt will include:
- `finding_id` — unique identifier for this finding (e.g., FIND-0005)
- `file_path` — path to the source file containing the vulnerable SQL query
- `line_number` — line number where the vulnerable query is located
- `language` — Java, Python, TypeScript, or Go
- `repo_url` — the repository URL to clone
- `service_name` — the service this file belongs to
- `cwe_id` — CWE-89 (SQL Injection)
- `title` — short description of the vulnerability
- `description` — detailed description including the vulnerable pattern found

## Procedure
1. Clone the repository from `repo_url` if not already present.
2. Read the finding details from the session prompt.
3. Update structured output: status="analyzing", progress_pct=10, current_step="Reading finding details".
4. Open the file at `file_path` and navigate to `line_number`.
5. Identify the vulnerable SQL query construction pattern:
   - String concatenation: `"SELECT * FROM users WHERE id = " + userId`
   - String interpolation/f-strings: `f"SELECT * FROM users WHERE id = {user_id}"`
   - String formatting: `"SELECT * FROM users WHERE id = %s" % user_id` (Python old-style — still vulnerable)
   - Template literals: `` `SELECT * FROM users WHERE id = ${userId}` `` (JS/TS)
6. Identify the database access framework being used:
   - Java/JDBC: `java.sql.Statement`, `java.sql.Connection`
   - Java/Spring: `JdbcTemplate`, Spring Data JPA `@Query`
   - Python/psycopg2: `cursor.execute()` with string formatting
   - Python/SQLAlchemy: `session.execute(text(...))` or raw SQL strings
   - Python/Django: `cursor.execute()` or raw queryset
   - TypeScript/pg: `client.query()` or `pool.query()`
   - TypeScript/mysql2: `connection.execute()`
   - Go/database-sql: `db.Query()`, `db.Exec()`
7. Scan the ENTIRE file (and related files in the same class/module) for other SQL queries using the same vulnerable pattern. Note all vulnerable locations.
8. Update structured output: status="analyzing", progress_pct=20, fix_approach=<description of what will be changed and how>, confidence=<assessment based on complexity>.
9. Create a new branch named `fix/FIND-{finding_id}-sql-injection` from the default branch.
10. Replace each vulnerable SQL query with its parameterized equivalent:

    **Java/JDBC:**
    ```java
    // BEFORE (vulnerable)
    Statement stmt = conn.createStatement();
    ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE id = " + userId);

    // AFTER (safe)
    PreparedStatement pstmt = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
    pstmt.setString(1, userId);
    ResultSet rs = pstmt.executeQuery();
    ```

    **Java/Spring JdbcTemplate:**
    ```java
    // BEFORE (vulnerable)
    jdbcTemplate.queryForObject("SELECT * FROM users WHERE id = " + userId, User.class);

    // AFTER (safe)
    jdbcTemplate.queryForObject("SELECT * FROM users WHERE id = ?", User.class, userId);
    ```

    **Python/psycopg2:**
    ```python
    # BEFORE (vulnerable)
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

    # AFTER (safe)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    ```

    **Python/SQLAlchemy:**
    ```python
    # BEFORE (vulnerable)
    session.execute(text(f"SELECT * FROM users WHERE id = {user_id}"))

    # AFTER (safe)
    session.execute(text("SELECT * FROM users WHERE id = :user_id"), {"user_id": user_id})
    ```

    **TypeScript/pg:**
    ```typescript
    // BEFORE (vulnerable)
    const result = await client.query(`SELECT * FROM users WHERE id = ${userId}`);

    // AFTER (safe)
    const result = await client.query('SELECT * FROM users WHERE id = $1', [userId]);
    ```

    **Go/database-sql:**
    ```go
    // BEFORE (vulnerable)
    rows, err := db.Query("SELECT * FROM users WHERE id = " + userId)

    // AFTER (safe)
    rows, err := db.Query("SELECT * FROM users WHERE id = $1", userId)
    ```

11. Update structured output: status="fixing", progress_pct=50, files_modified=<list of modified files>.
12. Add a unit test that verifies the fix:
    a. Test with a normal input value and verify correct SQL execution/results.
    b. Test with a SQL injection payload (e.g., `"'; DROP TABLE users; --"` or `"1 OR 1=1"`) and verify:
       - The query treats the payload as a literal string value, not executable SQL.
       - No SQL error is thrown from the injected syntax.
       - The query returns no results (or the expected safe result), not all rows.
13. Update structured output: status="testing", progress_pct=65, tests_added=<count>.
14. Run the full test suite:
    - Java: `mvn test` or `gradle test`
    - Python: `pytest` or `python -m pytest`
    - TypeScript: `npm test`
    - Go: `go test ./...`
15. If tests fail, analyze the failures and fix them.
16. Update structured output: status="testing", progress_pct=75, tests_passed=<true/false>, tests_added=<count>.
17. Commit all changes with message: `fix: parameterize SQL query to prevent injection [{finding_id}]`.
18. Push the branch to the remote.
19. Update structured output: status="creating_pr", progress_pct=90.
20. Create a pull request with:
    - Title: `fix: parameterize SQL query to prevent injection [{finding_id}]`
    - Body that includes:
      - Reference to CWE-89 (SQL Injection)
      - Description of the vulnerable pattern found
      - What was changed (concatenation → parameterized queries)
      - List of all query locations fixed (file, line number)
      - Tests added to verify the fix
21. Update structured output: status="completed", progress_pct=100, pr_url=<the PR URL>.

## Specifications
When the task is complete, ALL of the following must be true:
- No SQL query in the modified file(s) uses string concatenation or interpolation for user-supplied values.
- All SQL queries use parameterized queries / prepared statements with the appropriate placeholder syntax for the framework.
- At least one test exists that passes a SQL injection payload and verifies it is safely handled.
- All existing tests pass.
- A pull request exists on a feature branch (not main/master) with a clear title and body referencing the finding ID and CWE-89.
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
- After identifying all vulnerable queries: status="analyzing", progress_pct=20, fix_approach=<plan>, confidence=<assessment>
- After parameterizing queries: status="fixing", progress_pct=50, files_modified=<list>
- After adding tests: status="testing", progress_pct=65, tests_added=<count>
- After running test suite: status="testing", progress_pct=75, tests_passed=<bool>
- After creating PR: status="creating_pr", progress_pct=90, pr_url=<url>
- On completion: status="completed", progress_pct=100
- On failure at any step: status="failed", error_message=<what went wrong>

## Advice and Pointers
- Check for ALL SQL queries in the same file and class, not just the reported line. If one query is vulnerable, others in the same file are often vulnerable too.
- Be careful with IN clauses: `WHERE id IN (...)` with dynamic lists requires special handling. For JDBC, build the placeholder string dynamically (`?, ?, ?`). For Python/psycopg2, use `cursor.execute("... WHERE id = ANY(%s)", (list_of_ids,))`.
- For LIKE clauses, the `%` wildcard character must still be part of the parameter value, not the query string: `cursor.execute("SELECT * FROM t WHERE name LIKE %s", (f"%{search}%",))`.
- Watch for ORDER BY and column name injection — parameterized queries cannot protect dynamic column names. Use a whitelist of allowed column names instead.
- If the project uses an ORM (Hibernate, SQLAlchemy ORM, TypeORM, GORM), prefer ORM query methods over raw SQL where possible.
- Ensure the parameter types match what the database expects (e.g., integers for numeric columns).

## Forbidden Actions
- Do not commit directly to main or master branch. Always create a new feature branch.
- Do not disable, skip, or delete existing tests.
- Do not modify unrelated business logic.
- Do not introduce new dependencies without strong justification.
- Do not remove or weaken existing security controls.
- Do not replace parameterized queries with an allow-list/blocklist approach to sanitize input — parameterization is the correct fix.
- Do not use ORM `raw()` or `nativeQuery` with string concatenation as a "fix" — the query must be truly parameterized.

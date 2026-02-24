# Access Logging Remediation

## Overview
Add structured audit logging to data access paths (endpoints, DAOs, repository methods) that currently lack it, enabling security teams to trace who accessed what data, when, and with what result.

## What's Needed From User
The session prompt will include:
- `finding_id` — unique identifier for this finding (e.g., FIND-0015)
- `file_path` — path to the source file where audit logging is missing
- `line_number` — line number of the data access method/endpoint
- `language` — Java, Python, TypeScript, or Go
- `repo_url` — the repository URL to clone
- `service_name` — the service this file belongs to
- `cwe_id` — CWE-778 (Insufficient Logging)
- `title` — short description of the vulnerability
- `description` — detailed description of what data access path lacks logging

## Procedure
1. Clone the repository from `repo_url` if not already present.
2. Read the finding details from the session prompt.
3. Update structured output: status="analyzing", progress_pct=10, current_step="Reading finding details".
4. Open the file at `file_path` and navigate to `line_number`.
5. Identify the data access pattern:
   - REST endpoint / controller method
   - DAO / repository method (database access)
   - Service method accessing sensitive data
   - File I/O accessing sensitive files
6. Determine the existing logging framework used in the project:
   - Java: SLF4J with Logback (`LoggerFactory.getLogger(...)`) or Log4j2
   - Python: stdlib `logging` (`logging.getLogger(...)`) or `structlog`
   - TypeScript: `winston`, `pino`, `bunyan`, or `console.log`
   - Go: `log/slog`, `logrus`, or `zap`
   If the project already uses a logging framework, use that same framework. Do NOT introduce a new one.
7. Check if the project has an existing audit logging pattern:
   - Java Spring: `HandlerInterceptor`, `@Aspect`, or `AuditApplicationEvent`
   - Python Flask: `@app.before_request` / `@app.after_request`
   - Python Django: middleware
   - Express.js: middleware function
   - Go: middleware / HTTP handler wrapper
   If an existing pattern exists, follow it rather than adding inline logging.
8. Update structured output: status="analyzing", progress_pct=20, fix_approach=<plan describing where audit logs will be added, what framework/pattern will be used>, confidence=<assessment>.
9. Create a new branch named `fix/FIND-{finding_id}-access-logging` from the default branch.
10. Add a logger instance to the file if one does not already exist:

    **Java:**
    ```java
    private static final Logger logger = LoggerFactory.getLogger(UserController.class);
    ```

    **Python:**
    ```python
    import logging
    logger = logging.getLogger(__name__)
    ```

    **TypeScript (using project's framework):**
    ```typescript
    import { logger } from '../lib/logger'; // or whatever the project uses
    ```

    **Go:**
    ```go
    import "log/slog"
    ```

11. Add structured audit log entries at the appropriate points in the data access method. Each audit log entry must include these fields:

    **Required fields:**
    - `timestamp` — ISO 8601 format (usually provided by the logging framework)
    - `actor` — user ID, service account name, or "system" (extracted from request context, auth token, or session)
    - `action` — one of: "read", "write", "delete", "list", "update"
    - `resource` — what was accessed (table name, entity type, endpoint path)
    - `resource_id` — specific record ID if applicable, or "N/A"
    - `result` — "success", "failure", "denied", or record count for list operations

    **Optional fields (include if available from request context):**
    - `ip_address` — client IP from the request
    - `source` — calling service or origin

    **Log BEFORE the data access (intent):**
    ```python
    logger.info("audit.data_access", extra={
        "actor": request.user.id,
        "action": "read",
        "resource": "user_profile",
        "resource_id": user_id,
        "ip_address": request.remote_addr,
    })
    ```

    **Log AFTER the data access (result):**
    ```python
    logger.info("audit.data_access.complete", extra={
        "actor": request.user.id,
        "action": "read",
        "resource": "user_profile",
        "resource_id": user_id,
        "result": "success",
        "record_count": 1,
    })
    ```

    **Log on failure/exception:**
    ```python
    except Exception as e:
        logger.warning("audit.data_access.failed", extra={
            "actor": request.user.id,
            "action": "read",
            "resource": "user_profile",
            "resource_id": user_id,
            "result": "failure",
            "error": str(e),
        })
        raise
    ```

12. For Java Spring controllers, consider using this pattern:
    ```java
    @GetMapping("/users/{id}")
    public ResponseEntity<User> getUser(@PathVariable Long id, HttpServletRequest request) {
        String actor = SecurityContextHolder.getContext().getAuthentication().getName();
        logger.info("audit.data_access action=read resource=user resource_id={} actor={} ip={}",
            id, actor, request.getRemoteAddr());
        try {
            User user = userService.findById(id);
            logger.info("audit.data_access.complete action=read resource=user resource_id={} actor={} result=success",
                id, actor);
            return ResponseEntity.ok(user);
        } catch (Exception e) {
            logger.warn("audit.data_access.failed action=read resource=user resource_id={} actor={} result=failure error={}",
                id, actor, e.getMessage());
            throw e;
        }
    }
    ```

13. For Express.js middleware pattern:
    ```typescript
    function auditLog(action: string, resource: string) {
        return (req: Request, res: Response, next: NextFunction) => {
            const actor = req.user?.id || 'anonymous';
            const resourceId = req.params.id || 'N/A';
            logger.info({ actor, action, resource, resourceId, ip: req.ip }, 'audit.data_access');
            res.on('finish', () => {
                logger.info({
                    actor, action, resource, resourceId,
                    result: res.statusCode < 400 ? 'success' : 'failure'
                }, 'audit.data_access.complete');
            });
            next();
        };
    }

    router.get('/users/:id', auditLog('read', 'user'), getUserHandler);
    ```

14. Update structured output: status="fixing", progress_pct=50, files_modified=<list of modified files>.
15. Verify that the audit log entries do NOT contain sensitive data:
    - No passwords, tokens, or API keys in log entries.
    - No PII (emails, SSNs, credit cards) in log entries.
    - Resource IDs (like user_id) are acceptable — they are identifiers, not PII.
16. Update structured output: status="fixing", progress_pct=60, files_modified=<updated list>.
17. Add tests that verify audit logging works:

    **Python example:**
    ```python
    def test_audit_log_on_data_access(caplog):
        with caplog.at_level(logging.INFO):
            response = client.get("/users/123", headers={"Authorization": "Bearer test-token"})
        assert "audit.data_access" in caplog.text
        assert "user_profile" in caplog.text
        assert "read" in caplog.text
    ```

    **Java example:**
    ```java
    @Test
    void testAuditLogProduced() {
        LogCaptor logCaptor = LogCaptor.forClass(UserController.class);
        mockMvc.perform(get("/users/123").with(user("admin")))
            .andExpect(status().isOk());
        assertThat(logCaptor.getInfoLogs())
            .anyMatch(log -> log.contains("audit.data_access") && log.contains("resource=user"));
    }
    ```

18. Update structured output: status="testing", progress_pct=70, tests_added=<count>.
19. Run the full test suite.
20. If tests fail, fix the issues and re-run.
21. Update structured output: status="testing", progress_pct=75, tests_passed=<true/false>, tests_added=<count>.
22. Commit all changes with message: `fix: add audit logging to data access path [{finding_id}]`.
23. Push the branch to the remote.
24. Update structured output: status="creating_pr", progress_pct=90.
25. Create a pull request with:
    - Title: `fix: add audit logging to data access path [{finding_id}]`
    - Body that includes:
      - Reference to CWE-778 (Insufficient Logging)
      - What data access path was instrumented
      - Audit log fields included (actor, action, resource, result, etc.)
      - Logging framework and pattern used
      - Confirmation that no sensitive data is logged
      - Tests added
26. Update structured output: status="completed", progress_pct=100, pr_url=<the PR URL>.

## Specifications
When the task is complete, ALL of the following must be true:
- The identified data access path produces structured audit log entries on every invocation.
- Audit log entries include at minimum: timestamp, actor, action, resource, and result.
- Audit log entries do NOT contain sensitive data (no PII, passwords, tokens, or secrets).
- The logging uses the project's existing logging framework — no new logging dependencies introduced unless the project has none.
- If the project has an existing audit logging pattern (middleware, interceptor, decorator), the new logging follows that pattern.
- At least one test verifies that the audit log entry is produced with required fields.
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
- After identifying logging framework and pattern: status="analyzing", progress_pct=20, fix_approach=<plan>, confidence=<assessment>
- After adding audit log entries: status="fixing", progress_pct=50, files_modified=<list>
- After verifying no sensitive data in logs: status="fixing", progress_pct=60
- After adding tests: status="testing", progress_pct=70, tests_added=<count>
- After running test suite: status="testing", progress_pct=75, tests_passed=<bool>
- After creating PR: status="creating_pr", progress_pct=90, pr_url=<url>
- On completion: status="completed", progress_pct=100
- On failure at any step: status="failed", error_message=<what went wrong>

## Advice and Pointers
- Check if the project has an existing audit logging pattern first. It is much better to follow an existing middleware/interceptor/decorator pattern than to add inline logging to every method.
- For Java Spring, consider using `@Aspect` (AOP) with a pointcut on repository or controller methods to add audit logging without modifying business logic code.
- For Python Flask/Django, consider using `@app.before_request`/`@app.after_request` or Django middleware for request-level audit logging.
- For Express.js, use a middleware function that can be applied to specific routes or route groups.
- Use structured logging (JSON format) if the project's logging configuration supports it. This makes audit logs machine-parseable and searchable.
- The `actor` field should come from the authenticated user context (JWT claims, session, Spring SecurityContext). If no authentication context is available, use "anonymous" or "system".
- For write operations (POST, PUT, DELETE), consider logging a summary of what changed (e.g., "updated email field") without logging the actual values (which could be PII).
- If the endpoint handles batch operations (e.g., listing multiple records), log the count of records returned rather than individual IDs.

## Forbidden Actions
- Do not commit directly to main or master branch. Always create a new feature branch.
- Do not disable, skip, or delete existing tests.
- Do not modify unrelated business logic.
- Do not introduce new dependencies without strong justification.
- Do not remove or weaken existing security controls.
- Do not log sensitive data (PII, passwords, tokens, API keys) in audit log entries.
- Do not log the full request or response body — only log metadata (actor, action, resource, result).
- Do not introduce a new logging framework if the project already uses one.
- Do not add logging that significantly impacts performance (e.g., synchronous file I/O in a hot path). Use the existing async/buffered logging infrastructure.

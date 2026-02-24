# SPEC.md — Implementation Specification

This document expands the project plan into clearly separated phases and tasks, ready for delegation to coding subagents. Each task is self-contained with inputs, outputs, acceptance criteria, and file paths.

**Read `CLAUDE.md` first** — it contains the project overview, tech stack rules, design system, and API reference that all agents must follow.

---

## Completion Status

| Phase | Task | Status | Notes |
|-------|------|--------|-------|
| 0 | 0.1 Config (`config.py`) | DONE | Pydantic-settings, .env loading, all defaults |
| 0 | 0.2 Models (`models.py`) | DONE | All enums, Finding, RemediationSession, Wave, BatchRun |
| 1 | 1.1 CSV Parser (`parser.py`) | DONE | DictReader, enum validation, empty→None mapping |
| 1 | 1.2 Normalizer (`normalizer.py`) | DONE | Dedup by (service, file, line, category), higher severity wins |
| 1 | 1.3 Prioritizer (`prioritizer.py`) | DONE | In-place scoring, sorted return, range 25–85 |
| 1 | 1.4 Sample Data (`findings.csv`) | DONE | 20 rows, 3 services, 4/6/6/4 severity split |
| 2 | 2.1 Devin Client (`client.py`) | DONE | aiohttp wrapper, 429 retry, 204 handling, 7 methods |
| 2 | 2.2 Mock Client (`mock_devin_client.py`) | DONE | Interface parity, stage progression, 15% failure rate, category-aware output |
| 3 | 3.1 Batch Planner (`batch_planner.py`) | DONE | Chunking, 1-indexed waves, PENDING sessions |
| 3 | 3.2 Playbook Selector (`playbook_selector.py`) | DONE | Category mapping, fallback, async upload, assign_playbooks |
| 3 | 3.3 Playbooks (6 files) | DONE | All 7 sections, language-specific examples, structured output checkpoints |
| 4 | 4.1 Session Manager (`session_manager.py`) | DONE | Prompt builder, session creator, status interpreter, JSON Schema |
| 4 | 4.2 Wave Manager (`wave_manager.py`) | DONE | WaveManager class: execute_run, dispatch_wave, poll_wave, check_gate, retry_failed (retries only failed subset) |
| 5 | 5.1 Progress Tracker (`tracker.py`) | DONE | Atomic save_state, recount aggregation, timeline events, get_summary |
| 5 | 5.2 Poller (`poller.py`) | DONE | poll_session, poll_active_sessions, timeout detection, graceful errors |
| 6 | 6.1 CLI (`main.py`) | DONE | Click CLI: ingest, plan, run (--dry-run, --wave, --wave-size), status; lazy imports; asyncio.run bridge |
| 7 | 7.1 Dashboard Setup + Layout | DONE | Next.js init, sidebar, fonts, types, status-badge, API route, placeholders |
| 7 | 7.2–7.3 Dashboard Home + Findings | DONE | overview-cards (4 stat cards), sessions-table (top 10), findings-table (dual filters), use-status SWR hook |
| 7 | 7.4–7.5 Sessions + Review | DONE | Sessions list, session detail (breadcrumbs + status + progress + timeline), trace-timeline, pr-queue, sidebar PR badge |
| 8 | 8.1 E2E Mock Test | DONE | Full pipeline verified: 15 findings, 3 waves, 14/15 succeeded, state.json + dashboard confirmed |
| 8 | 8.2 CLIENT_SCENARIO.md | DONE | Professional client-facing document: discovery, solution, playbooks, guardrails, rollout, ROI |
| 8 | 8.3 Demo Script (demo.py) | DONE | One-command runner with accelerated mock timing (poll=3s, wave_size=5) |
| 8 | 8.4 asyncio.run fix | DONE | Consolidated to single event loop via _run_pipeline(); filterEvents null safety fixed |

---

## Phase 0: Data Models & Configuration

**Goal**: Establish the foundational data types and configuration that every other module depends on.

**No dependencies** — this phase must be completed first.

### Task 0.1: Configuration (`orchestrator/config.py`)

**File**: `orchestrator/config.py`

Implement `OrchestratorConfig` using `pydantic-settings` `BaseSettings`. All values should be configurable via environment variables with sensible defaults.

**Fields**:
```python
class OrchestratorConfig(BaseSettings):
    devin_api_key: str = ""
    devin_api_base_url: str = "https://api.devin.ai/v1"
    mock_mode: bool = True
    max_parallel_sessions: int = 10
    max_acu_per_session: int = 5
    poll_interval_seconds: int = 20
    session_timeout_minutes: int = 90
    min_success_rate: float = 0.7
    wave_size: int = 10
    slack_webhook_url: str = ""
    state_file_path: str = "./state.json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

**Acceptance criteria**:
- Loads from `.env` file if present
- All env vars map correctly (e.g., `DEVIN_API_KEY` → `devin_api_key`)
- Can be instantiated with no `.env` file (defaults work)

---

### Task 0.2: Data Models (`orchestrator/models.py`)

**File**: `orchestrator/models.py`

Define all Pydantic models used across the project. These are the shared types that every module imports.

**Models to implement**:

```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class FindingCategory(str, Enum):
    DEPENDENCY_VULNERABILITY = "dependency_vulnerability"
    SQL_INJECTION = "sql_injection"
    HARDCODED_SECRET = "hardcoded_secret"
    PII_LOGGING = "pii_logging"
    MISSING_ENCRYPTION = "missing_encryption"
    ACCESS_LOGGING = "access_logging"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    OTHER = "other"

class Finding(BaseModel):
    finding_id: str
    scanner: str
    category: FindingCategory
    severity: Severity
    title: str
    description: str
    service_name: str
    repo_url: str
    file_path: str
    line_number: int | None = None
    cwe_id: str | None = None
    dependency_name: str | None = None
    current_version: str | None = None
    fixed_version: str | None = None
    language: str | None = None
    priority_score: float = 0.0

class SessionStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    WORKING = "working"
    BLOCKED = "blocked"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

class RemediationSession(BaseModel):
    session_id: str | None = None
    finding: Finding
    playbook_id: str
    status: SessionStatus = SessionStatus.PENDING
    devin_url: str | None = None
    pr_url: str | None = None
    structured_output: dict | None = None
    wave_number: int = 0
    attempt: int = 1
    created_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

class Wave(BaseModel):
    wave_number: int
    sessions: list[RemediationSession]
    status: str = "pending"
    success_count: int = 0
    failure_count: int = 0

    @property
    def total_count(self) -> int:
        return len(self.sessions)

class BatchRun(BaseModel):
    run_id: str
    started_at: datetime
    waves: list[Wave]
    total_findings: int
    completed: int = 0
    successful: int = 0
    failed: int = 0
    prs_created: int = 0
    status: str = "pending"  # pending, running, completed, paused
    events: list[dict] = []  # Timeline events for the dashboard
```

**Acceptance criteria**:
- All models can be serialized with `.model_dump(mode='json')` (needed for state.json)
- Enums serialize as their string values
- `datetime` fields serialize to ISO format strings
- Can be deserialized back with `Model.model_validate(data)`

---

## Phase 1: Ingestion Pipeline

**Goal**: Parse a CSV of security findings into prioritized, normalized `Finding` objects.

**Depends on**: Phase 0 (models)

### Task 1.1: CSV Parser (`orchestrator/ingest/parser.py`)

**File**: `orchestrator/ingest/parser.py`

Parse a CSV file into a list of `Finding` objects. The CSV has columns matching the `Finding` model field names.

**Function signature**:
```python
def parse_findings_csv(file_path: str) -> list[Finding]:
    """Parse a CSV file of security findings into Finding objects.

    CSV columns: finding_id, scanner, category, severity, title, description,
    service_name, repo_url, file_path, line_number, cwe_id, dependency_name,
    current_version, fixed_version, language

    Empty cells for optional fields should be treated as None.
    """
```

**Implementation notes**:
- Use Python's built-in `csv.DictReader`
- Map empty strings to `None` for optional fields
- Convert `line_number` from string to `int | None`
- Validate `category` and `severity` values against the enums (skip rows with invalid values, log a warning)
- Return a list of `Finding` objects (priority_score not yet set — that's the prioritizer's job)

**Acceptance criteria**:
- Parses the `sample_data/findings.csv` file correctly
- Handles missing optional columns gracefully
- Skips rows with invalid category/severity, logs warning
- Returns list of valid `Finding` objects

---

### Task 1.2: Normalizer (`orchestrator/ingest/normalizer.py`)

**File**: `orchestrator/ingest/normalizer.py`

Validate and deduplicate findings. Light processing — the parser already creates Finding objects, but we need to catch duplicates and ensure data quality.

**Function signature**:
```python
def normalize_findings(findings: list[Finding]) -> list[Finding]:
    """Deduplicate and validate findings.

    Deduplication key: (service_name, file_path, line_number, category)
    If two findings share the same key, keep the one with higher severity.
    """
```

**Acceptance criteria**:
- Removes exact duplicates
- When two findings share the same dedup key, keeps the higher severity one
- Returns findings in their original order (minus removed duplicates)

---

### Task 1.3: Prioritizer (`orchestrator/ingest/prioritizer.py`)

**File**: `orchestrator/ingest/prioritizer.py`

Score each finding with a `priority_score` (0-100) based on severity, category, and service criticality. Sort by score descending.

**Function signature**:
```python
def prioritize_findings(findings: list[Finding]) -> list[Finding]:
    """Score and sort findings by priority.

    Score = severity_weight + category_weight + service_weight

    Severity weights: CRITICAL=40, HIGH=30, MEDIUM=15, LOW=5
    Category weights: sql_injection=25, hardcoded_secret=25, dependency_vulnerability=20,
                      pii_logging=15, missing_encryption=15, xss=20, path_traversal=20,
                      access_logging=10, other=10
    Service weights (configurable, example):
        payment-service=20, user-service=15, catalog-service=10, default=10

    Returns findings sorted by priority_score descending.
    """
```

**Implementation notes**:
- Service weights should use a dict with a default fallback for unknown services
- Mutate each finding's `priority_score` field before sorting
- Return a new sorted list (don't mutate the input list)

**Acceptance criteria**:
- Critical SQL injection in payment-service scores highest (40+25+20=85)
- Low access_logging in catalog-service scores lowest (5+10+10=25)
- Findings are sorted by `priority_score` descending

---

### Task 1.4: Sample Data (`sample_data/findings.csv`)

**File**: `sample_data/findings.csv`

Create a realistic CSV with ~20 security findings spanning 3 mock services and multiple categories.

**Requirements**:
- 3 services: `payment-service` (Java), `user-service` (Python), `catalog-service` (TypeScript)
- Mix of categories: ~8 dependency vulns, ~5 code-level (SQLi, XSS), ~4 PII/secrets, ~3 config
- Mix of severities: ~4 critical, ~6 high, ~6 medium, ~4 low
- Realistic file paths (e.g., `src/main/java/com/coupang/dao/UserDAO.java`)
- Realistic CWE IDs (e.g., CWE-89 for SQLi, CWE-502 for deserialization, CWE-798 for hardcoded secrets)
- For dependency vulns: include realistic dependency names, current and fixed versions

**Acceptance criteria**:
- Valid CSV that can be parsed by Task 1.1's parser
- At least 20 rows
- All three services represented
- All severity levels represented
- At least 4 different categories represented

---

## Phase 2: Devin API Client & Mock

**Goal**: Implement the Devin API wrapper and a mock client for development/testing.

**Depends on**: Phase 0 (models, config)

### Task 2.1: Devin API Client (`orchestrator/devin/client.py`)

**File**: `orchestrator/devin/client.py`

Async HTTP wrapper around the Devin v1 API.

**Class**: `DevinClient`

**Methods**:

```python
class DevinClient:
    def __init__(self, api_key: str, base_url: str = "https://api.devin.ai/v1"):
        ...

    async def create_session(
        self,
        prompt: str,
        playbook_id: str | None = None,
        tags: list[str] | None = None,
        structured_output_schema: dict | None = None,
        max_acu_limit: int | None = None,
        idempotent: bool = True,
    ) -> dict:
        """POST /v1/sessions → returns {session_id, url, is_new_session}"""

    async def get_session(self, session_id: str) -> dict:
        """GET /v1/sessions/{session_id} → returns full session details"""

    async def list_sessions(
        self, tags: list[str] | None = None, limit: int = 100, offset: int = 0
    ) -> dict:
        """GET /v1/sessions → returns paginated session list"""

    async def send_message(self, session_id: str, message: str) -> None:
        """POST /v1/sessions/{session_id}/message"""

    async def terminate_session(self, session_id: str) -> None:
        """DELETE /v1/sessions/{session_id}"""

    async def create_playbook(self, title: str, body: str) -> dict:
        """POST /v1/playbooks → returns {playbook_id, ...}"""

    async def list_playbooks(self) -> dict:
        """GET /v1/playbooks → returns list of playbooks"""

    async def close(self) -> None:
        """Close the aiohttp session"""
```

**Implementation notes**:
- Use `aiohttp.ClientSession` for all HTTP calls
- Set `Authorization: Bearer {api_key}` header on all requests
- Set `Content-Type: application/json` header
- Implement retry logic: on 429 (rate limit), wait and retry up to 3 times with exponential backoff
- On non-2xx responses, raise a descriptive exception with the status code and response body
- The `close()` method must close the aiohttp session (use as async context manager or call explicitly)

**Acceptance criteria**:
- All methods send correct HTTP method, URL path, headers, and JSON body
- Retry logic works for 429 responses
- Non-2xx errors raise descriptive exceptions
- `close()` cleans up the aiohttp session

---

### Task 2.2: Mock Devin Client (`mock/mock_devin_client.py`)

**File**: `mock/mock_devin_client.py`

Simulates the Devin API with realistic timing and state transitions. Used for development and demo when `MOCK_MODE=true`.

**Class**: `MockDevinClient` — same interface as `DevinClient`

**Behavior**:
- `create_session()`: Generates a fake `session_id` (e.g., `mock-{uuid[:8]}`), stores internal state, returns immediately. Each mock session progresses through stages over time: `analyzing` (5-10s) → `fixing` (10-20s) → `testing` (8-15s) → `creating_pr` (3-8s) → `completed`.
- `get_session()`: Returns current state based on elapsed time since creation. `status_enum` transitions from `working` → `finished`. `structured_output` updates with realistic data at each stage (progress_pct, current_step, etc.). `pull_request` appears when status is `completed` (with a fake GitHub PR URL).
- ~85% of mock sessions succeed, ~15% fail (for realistic demo — randomized at creation time).
- Failed sessions get stuck at the `testing` stage with `status_enum: "blocked"` and an error message.
- `send_message()`, `terminate_session()`: No-ops but tracked.
- `create_playbook()`: Returns a fake `playbook_id`.
- `list_sessions()`: Filters by tags if provided.

**Implementation notes**:
- Use `asyncio.sleep` is NOT needed — just track creation timestamps and compute state based on elapsed time when `get_session()` is called.
- Store sessions in an in-memory dict.
- Use `random.Random(seed)` for deterministic behavior in tests (accept optional seed in constructor).

**Acceptance criteria**:
- Same method signatures as `DevinClient`
- Sessions progress through stages based on elapsed time
- ~85% success rate, ~15% failure rate
- `structured_output` updates realistically at each stage
- Can be used as drop-in replacement for `DevinClient`

---

## Phase 3: Planning & Playbooks

**Goal**: Group prioritized findings into waves, assign playbooks, and write the playbook templates.

**Depends on**: Phase 0 (models), Phase 1 (prioritized findings)

### Task 3.1: Batch Planner (`orchestrator/planner/batch_planner.py`)

**File**: `orchestrator/planner/batch_planner.py`

Groups a sorted list of findings into waves of configurable size.

**Function signature**:
```python
def create_waves(
    findings: list[Finding],
    wave_size: int = 10,
) -> list[Wave]:
    """Group findings into waves.

    Findings should already be sorted by priority_score (highest first).
    Each wave contains up to wave_size findings.
    Wave numbers start at 1.
    """
```

**Implementation notes**:
- Simple chunking: first `wave_size` findings → Wave 1, next chunk → Wave 2, etc.
- Each `Wave` contains `RemediationSession` objects with `finding` set but `playbook_id` empty (set by playbook_selector).
- Set `wave_number` on each session.

**Acceptance criteria**:
- 20 findings with wave_size=5 → 4 waves
- Wave 1 gets the highest-priority findings
- All sessions have `status = PENDING`

---

### Task 3.2: Playbook Selector (`orchestrator/planner/playbook_selector.py`)

**File**: `orchestrator/planner/playbook_selector.py`

Maps finding categories to playbook IDs. In real mode, uploads playbooks via API on first run.

**Function signatures**:
```python
PLAYBOOK_MAP: dict[FindingCategory, str] = {
    FindingCategory.DEPENDENCY_VULNERABILITY: "playbooks/dependency_vulnerability.devin.md",
    FindingCategory.SQL_INJECTION: "playbooks/sql_injection.devin.md",
    FindingCategory.HARDCODED_SECRET: "playbooks/hardcoded_secrets.devin.md",
    FindingCategory.PII_LOGGING: "playbooks/pii_logging.devin.md",
    FindingCategory.MISSING_ENCRYPTION: "playbooks/missing_encryption.devin.md",
    FindingCategory.ACCESS_LOGGING: "playbooks/access_logging.devin.md",
    # XSS, PATH_TRAVERSAL, OTHER → use a generic fallback
}

async def ensure_playbooks_uploaded(client: DevinClient) -> dict[str, str]:
    """Upload playbooks to Devin if not already present.
    Returns a mapping of file path → playbook_id.
    In mock mode, returns fake playbook IDs."""

def assign_playbooks(
    waves: list[Wave],
    playbook_ids: dict[str, str],
) -> list[Wave]:
    """Set playbook_id on each session based on its finding's category."""
```

**Acceptance criteria**:
- Each finding category maps to the correct playbook file
- Categories without a specific playbook (XSS, PATH_TRAVERSAL, OTHER) use a fallback
- After `assign_playbooks`, every session has a non-empty `playbook_id`

---

### Task 3.3: Playbooks (6 files in `playbooks/`)

**Files**: `playbooks/*.devin.md`

Write 6 Devin playbook templates following the `.devin.md` format. Each playbook must include these sections:

1. **Overview**: What this playbook does (1-2 sentences)
2. **What's Needed From User**: What inputs Devin needs (provided in the session prompt)
3. **Procedure**: Step-by-step instructions (one action per line, imperative verbs)
4. **Specifications**: Post-conditions that must be true when done
5. **Advice and Pointers**: Tips for common pitfalls
6. **Forbidden Actions**: What Devin must NOT do

**Every playbook must also include**: Instructions for Devin to update structured output after each major step (analyzing, fixing, testing, creating_pr, completed/failed).

**Playbooks to write**:

1. **`dependency_vulnerability.devin.md`**: Upgrade a vulnerable dependency to the fixed version. Handle breaking API changes by consulting changelogs. Run tests. Create PR referencing CVE/CWE and finding ID.

2. **`sql_injection.devin.md`**: Replace string concatenation/interpolation in SQL queries with parameterized queries. Add a test that verifies injection payloads are safely handled. Cover Java/JDBC, Python/SQLAlchemy, Go/database-sql, TypeScript patterns.

3. **`hardcoded_secrets.devin.md`**: Externalize hardcoded secrets to environment variables. Add `.env.example` with placeholders. Ensure `.env` is in `.gitignore`. Add fail-fast validation at app boot if env var missing.

4. **`pii_logging.devin.md`**: Find PII (names, emails, phones, SSNs, credit cards) being logged via log statements or print calls. Replace with masked values or remove PII from logs. Add test verifying log output doesn't contain raw PII.

5. **`missing_encryption.devin.md`**: Identify data stored or transmitted without encryption. Add encryption annotations/calls (JPA `@Convert`, SQLAlchemy `EncryptedType`, etc.). Add tests verifying encrypted output.

6. **`access_logging.devin.md`**: Add audit logging to data access paths. Instrument DAO/repository methods with structured log entries (who, what, when, result). Follow existing logging framework patterns.

**Acceptance criteria**:
- Each playbook follows the section structure above
- Each playbook includes structured output update instructions
- Each playbook's Forbidden Actions section includes: "Do not commit directly to main/master", "Do not disable or skip existing tests", "Do not modify unrelated business logic"

---

## Phase 4: Wave Manager & Session Manager

**Goal**: Implement the core orchestration logic — dispatching waves, polling sessions, handling retries and gating.

**Depends on**: Phase 0, Phase 2 (client), Phase 3 (planner)

### Task 4.1: Session Manager (`orchestrator/devin/session_manager.py`)

**File**: `orchestrator/devin/session_manager.py`

Manages the lifecycle of a single Devin session: creating it, building the prompt, and interpreting results.

**Key functions/class**:

```python
# The structured output schema passed to every Devin session
REMEDIATION_OUTPUT_SCHEMA: dict  # JSON Schema Draft 7, see CLAUDE.md section 3.4

def build_remediation_prompt(finding: Finding) -> str:
    """Construct the session prompt from a Finding.

    Includes: finding ID, service, category, severity, file path, line number,
    CWE, description, and (for dependency vulns) dependency name/versions.
    Also includes instructions to update structured output after each step.
    """

async def create_remediation_session(
    client: DevinClient,  # or MockDevinClient
    session: RemediationSession,
    config: OrchestratorConfig,
) -> RemediationSession:
    """Create a Devin session for a remediation task.

    Builds the prompt, calls client.create_session(), updates the
    RemediationSession with session_id, devin_url, status=DISPATCHED.
    """

def interpret_session_status(details: dict) -> tuple[SessionStatus, str | None]:
    """Map Devin API status to our SessionStatus enum.

    working → WORKING
    finished → SUCCESS
    blocked → BLOCKED
    expired → TIMEOUT
    """
```

**Acceptance criteria**:
- `build_remediation_prompt` produces a clear, structured prompt with all finding details
- `REMEDIATION_OUTPUT_SCHEMA` is valid JSON Schema Draft 7
- `create_remediation_session` correctly calls the API and updates the session object
- `interpret_session_status` correctly maps all Devin status values

---

### Task 4.2: Wave Manager (`orchestrator/planner/wave_manager.py`)

**File**: `orchestrator/planner/wave_manager.py`

The heart of the orchestrator. Dispatches waves, polls sessions, handles gating and retries.

**Class**: `WaveManager`

```python
class WaveManager:
    def __init__(
        self,
        client: DevinClient,  # or MockDevinClient
        config: OrchestratorConfig,
        tracker: ProgressTracker,  # from monitor/tracker.py
    ):
        ...

    async def execute_run(self, batch_run: BatchRun) -> BatchRun:
        """Execute all waves in a batch run.

        For each wave:
        1. Dispatch all sessions (up to max_parallel_sessions concurrently)
        2. Poll until all sessions reach terminal state or timeout
        3. Update tracker with results
        4. Check success rate — if below threshold, pause and stop
        5. Retry failed sessions (up to max_retries=2)
        """

    async def dispatch_wave(self, wave: Wave) -> None:
        """Dispatch all sessions in a wave with concurrency control."""

    async def poll_wave(self, wave: Wave) -> None:
        """Poll all active sessions until they complete or timeout."""

    async def check_gate(self, wave: Wave) -> bool:
        """Return True if success rate meets threshold, False to pause."""
```

**Implementation notes**:
- Use `asyncio.Semaphore(config.max_parallel_sessions)` for concurrency control
- Use `asyncio.gather()` to dispatch sessions in parallel (within the semaphore limit)
- The poll loop checks each active session every `poll_interval_seconds`
- When a session reaches `finished`, update it to `SUCCESS` and record `pr_url` if present
- When a session reaches `blocked` or `expired`, update to `FAILED` or `TIMEOUT`
- After each session status change, call `tracker.update_session(session)` and `tracker.save_state()`
- After each wave completes, add a timeline event to `batch_run.events`

**Acceptance criteria**:
- Sessions are dispatched with concurrency control
- Polling correctly reads structured_output and status from each session
- Wave gating stops execution when success rate is below threshold
- Failed sessions are retried up to 2 times
- `tracker.save_state()` is called after every session status change

---

## Phase 5: Monitoring & State

**Goal**: Track aggregate progress and persist state to `state.json` for the dashboard.

**Depends on**: Phase 0 (models)

### Task 5.1: Progress Tracker (`orchestrator/monitor/tracker.py`)

**File**: `orchestrator/monitor/tracker.py`

Maintains the aggregate state of a batch run and writes it to `state.json`.

**Class**: `ProgressTracker`

```python
class ProgressTracker:
    def __init__(self, batch_run: BatchRun, state_file_path: str = "./state.json"):
        ...

    def update_session(self, session: RemediationSession) -> None:
        """Update aggregate counters based on session status change."""

    def add_event(self, event_type: str, message: str, details: dict | None = None) -> None:
        """Add a timeline event (for the dashboard trace timeline)."""

    def get_summary(self) -> dict:
        """Return aggregate stats for the dashboard overview cards."""

    def save_state(self) -> None:
        """Write the full BatchRun state to state.json (JSON serialized)."""
```

**State file format**: The full `BatchRun` model serialized via `batch_run.model_dump(mode='json')`. The dashboard reads this directly.

**Timeline events format**:
```python
{
    "timestamp": "2026-02-21T17:30:00Z",
    "event_type": "session_started",  # session_started, session_completed, session_failed, wave_started, wave_completed, wave_gated, run_started, run_completed
    "message": "Session FIND-0001 started for payment-service",
    "details": {"finding_id": "FIND-0001", "service": "payment-service", "wave": 1}
}
```

**Acceptance criteria**:
- `save_state()` writes valid JSON to the configured path
- `state.json` can be deserialized back to `BatchRun` via `BatchRun.model_validate(json.loads(...))`
- `get_summary()` returns correct aggregate counts
- Timeline events are appended in chronological order

---

### Task 5.2: Poller (`orchestrator/monitor/poller.py`)

**File**: `orchestrator/monitor/poller.py`

Async polling loop that checks all active sessions.

**Function**:
```python
async def poll_active_sessions(
    client: DevinClient,
    sessions: list[RemediationSession],
    tracker: ProgressTracker,
    config: OrchestratorConfig,
) -> list[RemediationSession]:
    """Poll all active sessions once.

    For each session with status DISPATCHED or WORKING:
    1. Call client.get_session(session_id)
    2. Update session.structured_output
    3. Update session.pr_url if pull_request present
    4. Update session.status based on status_enum
    5. If terminal state, set session.completed_at
    6. Call tracker.update_session() and tracker.save_state()

    Returns list of still-active sessions (non-terminal).
    """
```

**Acceptance criteria**:
- Only polls sessions in DISPATCHED or WORKING status
- Correctly maps Devin status to our SessionStatus
- Updates structured_output on each poll
- Handles API errors gracefully (log, don't crash)
- Returns only still-active sessions

---

## Phase 6: CLI Entry Point

**Goal**: Wire everything together into a Click CLI.

**Depends on**: Phase 0-5

### Task 6.1: CLI (`orchestrator/main.py`)

**File**: `orchestrator/main.py`

Click-based CLI that ties all modules together.

**Commands**:

```python
@click.group()
def cli():
    """Coupang Security Remediation Orchestrator"""

@cli.command()
@click.argument("csv_path", type=click.Path(exists=True))
def ingest(csv_path):
    """Parse and prioritize findings from a CSV file.
    Outputs summary to stdout."""

@cli.command()
@click.argument("csv_path", type=click.Path(exists=True))
@click.option("--wave-size", default=10, help="Findings per wave")
def plan(csv_path, wave_size):
    """Generate wave-based remediation plan. Outputs plan summary to stdout."""

@cli.command()
@click.argument("csv_path", type=click.Path(exists=True))
@click.option("--wave", type=int, default=None, help="Run only a specific wave")
@click.option("--dry-run", is_flag=True, help="Show what would be dispatched")
def run(csv_path, wave, dry_run):
    """Full pipeline: ingest → plan → dispatch → monitor.
    This is the main command for the demo."""

@cli.command()
def status():
    """Show current progress from state.json."""
```

**Implementation notes**:
- `run` command should: parse CSV → normalize → prioritize → create waves → assign playbooks → execute run (via WaveManager) → save final state
- Use `asyncio.run()` to run the async wave manager from the sync Click context
- Determine which client to use based on `config.mock_mode`: `MockDevinClient` if True, `DevinClient` if False
- Print progress to stdout as waves complete (e.g., "Wave 1: 5/5 complete, 4 success, 1 failed, 4 PRs created")
- The `status` command reads `state.json` and prints a formatted summary

**Acceptance criteria**:
- `python -m orchestrator.main ingest sample_data/findings.csv` parses and shows summary
- `python -m orchestrator.main plan sample_data/findings.csv` shows wave plan
- `python -m orchestrator.main run sample_data/findings.csv` (with MOCK_MODE=true) runs full pipeline and produces state.json
- `python -m orchestrator.main status` reads and displays state.json

---

## Phase 7: Next.js Dashboard

**Goal**: Build a polished dashboard that reads `state.json` and displays real-time remediation progress.

**Depends on**: Phase 5 (state.json format)

**Design reference**: See `CLAUDE.md` Design System section. The UI must match the "Action" dashboard aesthetic: Baskerville titles, Inter body, white bg, thin card borders, green/red status badges, left sidebar nav.

### Task 7.1: Dashboard Setup & Layout

**Files**: `dashboard/` (initialize Next.js app)

- Init Next.js app with App Router, Tailwind CSS, TypeScript
- Install and configure shadcn/ui
- Configure fonts: Baskerville (serif) via `next/font/local` or Google Fonts for titles, Inter for body
- Set up Tailwind theme colors to match design system
- Create `lib/types.ts` with TypeScript types matching the Python models (BatchRun, Wave, RemediationSession, Finding, etc.)
- Create `lib/fonts.ts` for font configuration
- Create `app/layout.tsx` with sidebar + main content area
- Create `components/sidebar.tsx`: Left nav with items: Dashboard (grid icon), Findings (list icon), Sessions (play icon), Review (users icon). Active state highlighting. App name in Baskerville italic at top.

**Acceptance criteria**:
- `npm run dev` starts without errors
- Sidebar renders with correct nav items
- Fonts load correctly (Baskerville for title, Inter for body)
- No shadcn/ui errors

---

### Task 7.2: API Route & Data Types

**Files**: `dashboard/app/api/status/route.ts`, `dashboard/lib/types.ts`

API route that reads `state.json` and returns it. The dashboard frontend will poll this every 5 seconds.

```typescript
// app/api/status/route.ts
export async function GET() {
    // Read ../state.json (path relative to project root)
    // If file doesn't exist, return a default empty state
    // Return JSON response
}
```

**Also create**: `dashboard/lib/types.ts` with TypeScript interfaces for all Python models:
- `Finding`, `RemediationSession`, `Wave`, `BatchRun`, `TimelineEvent`
- These must match the JSON serialization from Python's `model_dump(mode='json')`

**Acceptance criteria**:
- GET `/api/status` returns valid JSON matching BatchRun structure
- Returns empty/default state if `state.json` doesn't exist yet
- Types in `lib/types.ts` match Python model serialization

---

### Task 7.3: Dashboard Home Page

**Files**: `dashboard/app/page.tsx`, `dashboard/components/overview-cards.tsx`, `dashboard/components/sessions-table.tsx`, `dashboard/components/status-badge.tsx`

**Overview cards** (4 in a row):
1. "Total Findings" — large number, sub-stats: "Critical X High Y Medium Z"
2. "Active Sessions" — large number, sub-stats: "Working X Completed Y Failed Z"
3. "Pending Reviews" — large number (count of sessions with PR but not yet merged)
4. "Success Rate" — large percentage, sub-stats: "Completed X Failed Y"

**Recent Sessions table**: Latest 10 sessions showing: Finding title, Service, Status badge, Started time, Duration. Clickable rows → `/sessions/[id]`.

**Status badge component**: Reusable pill badge — green "Completed", amber "Working", red "Failed", gray "Pending".

**Data fetching**: Use `fetch('/api/status')` with polling every 5 seconds (use SWR with `refreshInterval: 5000` or a custom hook).

**Acceptance criteria**:
- Page renders with 4 overview cards + sessions table
- Cards show large Baskerville numbers with small sub-stats
- Table auto-refreshes every 5 seconds
- Status badges use correct colors
- Works with empty state (shows zeros)

---

### Task 7.4: Findings Page

**Files**: `dashboard/app/findings/page.tsx`, `dashboard/components/findings-table.tsx`

Full findings table with columns: Finding ID, Title, Service, Category, Severity (badge), Status, Session link.

Filterable by severity (dropdown) and category (dropdown).

**Acceptance criteria**:
- All findings from state.json displayed in table
- Severity filter works (Critical, High, Medium, Low, All)
- Category filter works
- Baskerville page title "Findings"

---

### Task 7.5: Sessions Page & Detail

**Files**: `dashboard/app/sessions/page.tsx`, `dashboard/app/sessions/[id]/page.tsx`, `dashboard/components/session-detail.tsx`, `dashboard/components/trace-timeline.tsx`

**Sessions list page**: Table with columns: Finding, Service, Status badge, Started, Duration, PR link.

**Session detail page** (`/sessions/[id]`):
- Breadcrumb: "Sessions / {session_id}"
- Page title: "{Finding title} — {session_id}" in Baskerville
- **Session Status card**: Status badge, Created time, Completed time, Duration (matching Action's "Run Status" pattern)
- **Devin Progress card**: Current step, progress %, fix approach, files modified, tests passed/added, confidence
- **Trace Timeline** (matching Action's trace timeline): Chronological list of events with colored dots + status badges + timestamps. Events: Session Started, Analyzing Finding, Applying Fix, Running Tests, Creating PR, Session Completed/Failed.

**Acceptance criteria**:
- Sessions list shows all sessions with correct statuses
- Clicking a row navigates to detail page
- Detail page shows all structured output data
- Trace timeline renders events chronologically
- Works with in-progress sessions (partial data)

---

### Task 7.6: Review Page

**Files**: `dashboard/app/review/page.tsx`, `dashboard/components/pr-queue.tsx`

PR review queue showing sessions that have created PRs.

Table columns: Finding, Service, Severity badge, PR Link (GitHub URL), Confidence, Status.

Sidebar nav should show a notification count badge (number of pending reviews) in red, matching Action's pattern.

**Acceptance criteria**:
- Shows only sessions with non-null `pr_url`
- PR links open in new tab
- Notification count in sidebar reflects pending review count
- Baskerville page title "Review"

---

## Phase 8: Integration & Demo

**Goal**: Wire everything together for the end-to-end demo.

**Depends on**: All previous phases

### Task 8.1: End-to-End Mock Test

Run the full pipeline with `MOCK_MODE=true`:
1. `python -m orchestrator.main run sample_data/findings.csv`
2. Verify `state.json` is created and updated
3. Start Next.js dashboard: `cd dashboard && npm run dev`
4. Open `http://localhost:3000` — verify all pages render with data from state.json
5. Verify auto-refresh works (state.json updates → dashboard updates)

### Task 8.2: Client Scenario Document

**File**: `CLIENT_SCENARIO.md`

Write the full client scenario document including:
- Discovery assumptions
- Client pain statement
- Proposed automation workflow
- Progress visibility/reporting loop
- Validation/rollout plan
- ROI analysis

### Task 8.3: Demo Script

**File**: `scripts/demo.py`

One-command demo runner that:
1. Creates a fresh state.json
2. Runs the orchestrator in mock mode with accelerated timing
3. Suitable for running alongside the dashboard during video recording

---

## Dependency Graph

```
Phase 0 (Models + Config)
    ↓
    ├── Phase 1 (Ingestion) ──────────────┐
    ├── Phase 2 (Devin Client + Mock) ────┤
    └── Phase 3 (Planner + Playbooks) ────┤
                                           ↓
                                    Phase 4 (Wave Manager)
                                           ↓
                                    Phase 5 (Monitor + State)
                                           ↓
                                    Phase 6 (CLI)
                                           ↓
                                    Phase 7 (Dashboard) ← can start once state.json format is defined (after Phase 5)
                                           ↓
                                    Phase 8 (Integration)
```

**Parallelizable phases**: Phases 1, 2, and 3 can all run in parallel (they only depend on Phase 0). Phase 7 can start once Phase 5 defines the state.json format.

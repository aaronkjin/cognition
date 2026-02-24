# Cognition Take-Home Plan: Coupang Security Remediation Orchestrator

## Context

This is a take-home project for Cognition (makers of Devin). We must build a working automation using Devin + Devin API and record a 5-10 minute Loom video presenting it as a client-facing solution. Per the project notes, we're creating a custom client scenario for a real Korean company (not using the given A-E scenarios), leveraging a parallelized Devin agent swarm.

Why Coupang: In November 2025, Coupang disclosed a breach exposing 33.7 million customer records. Korean lawmakers are advancing PIPA amendments raising fines to 10% of annual revenue with personal CEO liability. Coupang operates 600+ microservices in Java/Python/Go/TypeScript/Kotlin on AWS. This creates an urgent, real-world scenario where Devin's parallel agent capabilities directly address the pain: systematically remediating 2,000+ security findings across hundreds of services before a regulatory audit.

Devin Access: Free trial under "Aaron Jin Demo" account with 500 ACUs remaining (1 ACU ~ 15 min active Devin work). We will use real Devin sessions for the demo to show actual capability, not just simulated output.

---

## 1) Client Scenario: Coupang — "We have 2,000 security findings and 4 months before the FSS audit"

### Discovery Assumptions

| Dimension           | Detail                                                                                                           |
| ------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Company             | Coupang — Korea's largest e-commerce platform                                                                    |
| Scale               | 600+ microservices, polyglot codebase (Java/Spring, Python, Go, TypeScript, Kotlin)                              |
| Incident            | Nov 2025: 33.7M customer records exposed                                                                         |
| Regulatory pressure | PIPA fines rising to 10% of revenue; CEO personal liability; FSS audit in Q2 2026                                |
| Security backlog    | ~2,000 open findings from SonarQube, Snyk, and CodeQL                                                            |
| Finding breakdown   | Dependency vulns (40%), code-level patterns like SQLi/XSS (30%), PII/data protection (20%), config/secrets (10%) |
| Current bottleneck  | Platform engineers focused on reliability/features; security findings pile up unfixed                            |
| CI/CD maturity      | Strong — automated tests, CI pipelines per service (confirmed by Coupang engineering blog)                       |
| Compliance needs    | All remediation must be auditable; CISO + service owner review required before merge                             |
| Timeline            | 4 months before FSS audit                                                                                        |

### Client Pain Statement (Hypothetical)

> "We just went through a major data incident. Our CISO's security team has identified 2,000+ security findings across our 600+ microservices — vulnerable dependencies, hardcoded secrets, SQL injection patterns, insufficient data access logging, missing encryption, and PII exposure in logs. Our scanners flag dozens of new issues weekly. But our platform engineers are heads-down on reliability and the upcoming holiday season. We need to systematically remediate these findings before the FSS audit in Q2, or we face fines that could be 10% of our annual revenue."

---

## 2) Solution Architecture: Wave-Based Parallel Agent Swarm

### Input Format: CSV (Primary) + JSON (Internal)

The user-facing input is a CSV file, the kind of export a security team would produce from a spreadsheet (Google Sheets/Excel) or scanner dashboard.

Expected CSV columns:

`finding_id,scanner,category,severity,title,description,service_name,repo_url,file_path,line_number,cwe_id,dependency_name,current_version,fixed_version,language`

Example rows:

```csv
FIND-0001,snyk,dependency_vulnerability,critical,Vulnerable log4j-core 2.14.1,Remote code execution via Log4Shell,payment-service,https://github.com/org/payment-service,pom.xml,42,CWE-502,log4j-core,2.14.1,2.17.1,java
FIND-0002,sonarqube,sql_injection,critical,SQL Injection in UserDAO.java,String concatenation in SQL query,payment-service,https://github.com/org/payment-service,src/main/java/com/coupang/dao/UserDAO.java,87,CWE-89,,,,java
```

Ingest flow: CSV -> Parse -> Normalize -> Deduplicate -> Score -> Prioritize -> internal JSON finding objects.

### High-Level Flow

```text
CSV Export (Google Sheets / Excel / Scanner Dashboard)
        |
        v
[INGEST & TRIAGE]
  CSV -> Parse -> Normalize -> Deduplicate -> Score -> Prioritize
        |
        v
[WAVE PLANNER]
  Group by severity -> Assign playbooks -> Create wave batches
  Wave 1: Critical (SQLi, hardcoded secrets)
  Wave 2: High (dependency vulns)
  Wave 3: Medium (PII logging, missing encryption)
  Wave N: Low (access logging, config)
        |
        v
[DEVIN SESSION DISPATCH]
  Up to 10 parallel sessions per wave, each with finding-specific playbook
  Each session outputs a PR
        |
        v
[MONITOR & REPORT]
  Structured output polling every 20s
  - Per-session: status, progress%, current_step
  - Per-wave: success rate, PRs created
  - Overall: completion%, severity breakdown
  Wave gating: success_rate >= 70% to continue
  Slack + dashboard visibility
```

### Key Design Decisions

1. **One finding = one Devin session:** Best fit for small, clearly scoped tasks with verifiable outcomes.
2. **Wave-based dispatch with gating:** Priority waves (10 sessions/wave) and stop if success rate <70%.
3. **Structured output tracking:** Session JSON states (`analyzing` -> `fixing` -> `testing` -> `creating_pr` -> terminal state).
4. **Playbook-driven remediation:** Category -> reusable `.devin.md` playbooks with forbidden actions.
5. **Idempotent sessions:** `idempotent: true` to avoid duplicate work during retries/restarts.

---

## 3) Technical Implementation

### 3.1 Project Structure

```text
cognition-takehome/
├── INSTRUCTIONS.md                          # existing
├── RESEARCH.md                              # existing
├── EXAMPLE_CLIENT_SCENARIO_REFERENCE.md     # existing
├── CLIENT_SCENARIO.md                       # Coupang scenario writeup
│
├── orchestrator/                            # Python orchestrator
│   ├── __init__.py
│   ├── main.py                              # CLI entry point (click)
│   ├── config.py                            # Pydantic settings (env-based)
│   ├── models.py                            # Data models (Finding, Session, Wave, Run)
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── parser.py                        # Parse CSV input (primary) + JSON fallback
│   │   ├── normalizer.py                    # Validate & normalize to Finding objects
│   │   └── prioritizer.py                   # Severity + category + service scoring
│   ├── planner/
│   │   ├── __init__.py
│   │   ├── batch_planner.py                 # Group findings into waves
│   │   ├── playbook_selector.py             # Map category -> playbook_id
│   │   └── wave_manager.py                  # Wave dispatch + gating + retry
│   ├── devin/
│   │   ├── __init__.py
│   │   ├── client.py                        # Devin API v1 wrapper (aiohttp)
│   │   └── session_manager.py               # Session lifecycle (create, poll, retry, terminate)
│   └── monitor/
│       ├── __init__.py
│       ├── poller.py                        # Async structured output polling loop
│       ├── tracker.py                       # Aggregated progress state -> writes state.json
│       └── notifier.py                      # Slack webhook (stretch goal)
│
├── dashboard/                               # Next.js dashboard
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── findings/page.tsx
│   │   ├── sessions/page.tsx
│   │   ├── sessions/[id]/page.tsx
│   │   ├── review/page.tsx
│   │   └── api/status/route.ts             # Reads state.json
│   ├── components/
│   │   ├── sidebar.tsx
│   │   ├── overview-cards.tsx
│   │   ├── sessions-table.tsx
│   │   ├── findings-table.tsx
│   │   ├── session-detail.tsx
│   │   ├── trace-timeline.tsx
│   │   ├── pr-queue.tsx
│   │   └── status-badge.tsx
│   └── lib/
│       ├── types.ts
│       └── fonts.ts
│
├── playbooks/
│   ├── dependency_vulnerability.devin.md
│   ├── sql_injection.devin.md
│   ├── hardcoded_secrets.devin.md
│   ├── pii_logging.devin.md
│   ├── missing_encryption.devin.md
│   └── access_logging.devin.md
│
├── sample_data/
│   ├── findings.csv                         # primary input
│   └── findings.json                        # JSON mirror
│
├── mock/
│   ├── __init__.py
│   └── mock_devin_client.py
│
├── scripts/
│   ├── seed_findings.py
│   └── demo.py
│
├── tests/
│   ├── test_parser.py
│   ├── test_prioritizer.py
│   ├── test_batch_planner.py
│   └── test_session_manager.py
│
├── pyproject.toml
├── requirements.txt
└── .env.example
```

### 3.2 Core Data Models (`models.py`)

```python
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
    line_number: int | None
    cwe_id: str | None
    dependency_name: str | None
    current_version: str | None
    fixed_version: str | None
    language: str | None
    priority_score: float = 0.0

class RemediationSession(BaseModel):
    session_id: str | None
    finding: Finding
    playbook_id: str
    status: str = "pending"  # pending|dispatched|working|success|failed|timeout
    devin_url: str | None
    pr_url: str | None
    structured_output: dict | None
    wave_number: int
    attempt: int = 1
    created_at: datetime | None
    completed_at: datetime | None

class Wave(BaseModel):
    wave_number: int
    sessions: list[RemediationSession]
    status: str = "pending"
    success_count: int = 0
    failure_count: int = 0

class BatchRun(BaseModel):
    run_id: str
    started_at: datetime
    waves: list[Wave]
    total_findings: int
    completed: int = 0
    successful: int = 0
    failed: int = 0
    prs_created: int = 0
```

### 3.3 Devin API Client (`devin/client.py`)

Thin async wrapper around Devin v1 API:

| Method                | API Call                         | Purpose                                                                                                     |
| --------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `create_session()`    | `POST /v1/sessions`              | Create session with prompt, playbook_id, tags, structured_output_schema, `max_acu_limit`, `idempotent=True` |
| `get_session()`       | `GET /v1/sessions/{id}`          | Poll status, structured output, pull request                                                                |
| `list_sessions()`     | `GET /v1/sessions?tags=...`      | List sessions by wave/category tags                                                                         |
| `send_message()`      | `POST /v1/sessions/{id}/message` | Send follow-up guidance to stuck sessions                                                                   |
| `terminate_session()` | `DELETE /v1/sessions/{id}`       | Kill timed-out sessions                                                                                     |
| `create_playbook()`   | `POST /v1/playbooks`             | Upload playbook templates                                                                                   |
| `list_playbooks()`    | `GET /v1/playbooks`              | Check existing playbooks                                                                                    |

Authentication: `Authorization: Bearer {DEVIN_API_KEY}`.

### 3.4 Structured Output Schema

```json
{
  "type": "object",
  "properties": {
    "finding_id": { "type": "string" },
    "status": {
      "type": "string",
      "enum": [
        "analyzing",
        "fixing",
        "testing",
        "creating_pr",
        "completed",
        "failed"
      ]
    },
    "progress_pct": { "type": "integer", "minimum": 0, "maximum": 100 },
    "current_step": { "type": "string" },
    "fix_approach": { "type": "string" },
    "files_modified": { "type": "array", "items": { "type": "string" } },
    "tests_passed": { "type": ["boolean", "null"] },
    "tests_added": { "type": "integer" },
    "pr_url": { "type": ["string", "null"] },
    "error_message": { "type": ["string", "null"] },
    "confidence": { "type": "string", "enum": ["high", "medium", "low"] }
  },
  "required": ["finding_id", "status", "progress_pct", "current_step"]
}
```

Polling cadence: `GET /v1/sessions/{id}` every 20 seconds.

### 3.5 Wave Manager (Core Orchestration Logic)

```python
async def execute_run(waves: list[Wave]):
    for wave in waves:
        semaphore = asyncio.Semaphore(config.max_parallel_sessions)  # default: 10
        await asyncio.gather(*[
            dispatch_session(s, semaphore) for s in wave.sessions
        ])

        await poll_until_complete(wave)

        rate = wave.success_count / wave.total_count
        notify_slack(wave_summary(wave))

        if rate < config.min_success_rate:  # default: 0.7
            notify_slack(f"Wave {wave.wave_number} success rate {rate:.0%} — pausing for review")
            break

        for s in wave.sessions:
            if s.status == "failed" and s.attempt < config.max_retries:
                await retry_session(s)
```

### 3.6 Playbooks (3 Key Examples)

- `dependency_vulnerability.devin.md`: Upgrade vulnerable dependency to fixed version, handle breakages, run tests, create PR with CVE/finding ID.
- `sql_injection.devin.md`: Replace string-concatenated SQL with parameterized queries; add injection test coverage (Java/Python/Go/TypeScript patterns).
- `hardcoded_secrets.devin.md`: Externalize secrets to env vars, update `.env.example`, ensure `.env` in `.gitignore`, add startup validation.

All playbooks include: Overview, Procedure, Specifications, Advice, Forbidden Actions.

### 3.7 Dashboard (Next.js + shadcn/ui)

Architecture: Python orchestrator writes `state.json`; Next.js reads via `/api/status`; frontend auto-refreshes every 5 seconds.

Design system:

- Baskerville for logo/title moments; Inter for body/table content.
- White/off-white background, black text, green success/red failed badges, subtle borders.
- Left sidebar layout + clean tables/cards.

Sidebar/pages:

1. **Dashboard**: 4 summary cards + recent sessions table.
2. **Findings**: full findings table with filters.
3. **Sessions**: run list + detail pages (`status`, `progress`, trace timeline).
4. **Review**: PR queue awaiting CISO/owner approval.

Data flow: Python orchestrator -> `state.json` -> Next.js API route -> React frontend (SWR polling every 5s).

### 3.8 Slack Notifications (Stretch Goal)

- Wave complete summaries
- Gating alerts (below threshold)
- Final run report with ROI metrics

If skipped, dashboard + CLI are primary visibility surfaces.

### 3.9 ACU Budget Plan (500 ACUs)

| Usage                   |         ACUs | Notes                                          |
| ----------------------- | -----------: | ---------------------------------------------- |
| Development/testing     |       ~30-50 | Iterating playbooks/session creation/debugging |
| Playbook validation     |       ~30-40 | 6 playbooks x ~5 ACU each                      |
| Demo recording sessions |       ~50-80 | 5-8 real sessions during Loom                  |
| Buffer for retries      |          ~30 | Failed sessions/re-runs                        |
| **Total planned**       | **~140-200** |                                                |
| **Remaining reserve**   |    **~300+** | Comfortable margin                             |

ACU conservation strategies:

- `max_acu_limit: 5` per session.
- Build/test orchestrator logic with `MockDevinClient` first.
- Validate each playbook once before full demo.
- Use `idempotent: true` to avoid duplicate sessions.

### 3.10 Demo Strategy (Real Devin + Mock Hybrid)

Step 1: Create 3 mock repos with planted vulnerabilities:

| Repo                      | Language           | Planted Vulnerabilities                              |
| ------------------------- | ------------------ | ---------------------------------------------------- |
| `coupang-payment-service` | Java/Spring        | SQLi in DAO, hardcoded DB password, vulnerable log4j |
| `coupang-user-service`    | Python/Flask       | PII in logs, hardcoded API key, vulnerable requests  |
| `coupang-catalog-service` | TypeScript/Express | Path traversal, vulnerable lodash                    |

Step 2: Connect repos to Devin (GitHub integration).  
Step 3: Generate Devin API key.  
Step 4: Hybrid demo:

- 5-8 real Devin sessions (real PRs)
- 12-15 mock sessions (fleet scale simulation)
- Pre-cook 2-3 completed sessions before recording

---

## 4) Demo Video Script (5-10 min Loom)

| Timestamp  | Section         | Content                                                                |
| ---------- | --------------- | ---------------------------------------------------------------------- |
| 0:00-1:30  | Context         | Coupang breach + 2,000 findings + 4-month deadline + regulatory stakes |
| 1:30-3:00  | Ingest & Plan   | Run orchestrator, show parse/prioritize/wave planning                  |
| 3:00-5:30  | Live Dispatch   | Show live Devin sessions + dashboard updates                           |
| 5:30-7:00  | Results         | Show completed sessions + real GitHub PR diff/tests                    |
| 7:00-8:30  | Dashboard & ROI | Progress, severity breakdown, PR queue, ROI estimate                   |
| 8:30-10:00 | Next Steps      | Pilot -> Scale -> Ongoing; mention VPC deployment for compliance       |

---

## 5) Rollout Plan (Client Presentation)

| Phase   | Timeline  | Scope                                                | Goal                                                   |
| ------- | --------- | ---------------------------------------------------- | ------------------------------------------------------ |
| Pilot   | Weeks 1-2 | 50 highest-severity findings across 10 services      | Validate playbooks, measure success rate, tune prompts |
| Scale   | Weeks 3-8 | Full 2,000 finding remediation, 10 parallel sessions | Clear backlog before Q2 FSS audit                      |
| Ongoing | Week 9+   | CI-connected auto-trigger on new scanner findings    | Keep backlog flat, continuous compliance posture       |

### Enterprise Considerations

- Deployment: customer-hosted VPC or dedicated SaaS with PrivateLink for PIPA data residency.
- RBAC: scoped service users/permissions for CISO vs security engineering roles.
- Audit: full session audit logs + tag-based analytics for compliance reporting.
- Human review: all PRs require CISO team + service owner approval before merge.

---

## 6) Implementation Tasks (2-3 Day Plan)

### Day 1: Foundation + Orchestrator Core

**Morning: Setup & Devin Access**

- Connect GitHub to Devin
- Generate API key
- Create 3 mock repos with vulnerabilities
- Grant Devin repo access
- Initialize project (`pyproject.toml`, `requirements.txt`, dirs)
- Implement `config.py`, `models.py`

**Afternoon: API + Ingestion + Planning**

- Implement `devin/client.py` async wrapper
- Implement `mock/mock_devin_client.py`
- Create `sample_data/findings.csv` (~20 findings)
- Implement parser/normalizer/prioritizer
- Implement batch planner + playbook selector
- Write 3 core playbooks

**Evening: Core Orchestration**

- Implement wave manager (dispatch/gating/retry)
- Implement session manager lifecycle
- Implement poller/tracker (`state.json`)
- Implement CLI in `main.py`
- End-to-end test with mock client

### Day 2: Dashboard + Live Devin Integration

**Morning: Next.js Dashboard**

- Initialize dashboard app + shadcn/ui components
- Configure fonts/theme/layout
- Build sidebar, API route, overview cards, sessions table

**Afternoon: Real Devin Integration**

- API smoke test (`POST /v1/sessions`, poll status)
- Upload/test playbooks
- Run 2-3 real sessions against mock repos
- Fix playbook issues
- Write remaining playbooks

**Evening: Integration + Polish**

- Switch orchestrator to real Devin API
- Run hybrid demo (5 real + 10 mock)
- Verify dashboard real-time updates
- Build session detail/findings/review pages
- Add shared TS types

### Day 3: Demo + Recording

**Morning: End-to-End Dry Run**

- Pre-run 2-3 sessions to completion
- Full dry run: ingest -> plan -> dispatch -> dashboard -> PRs
- Time against 5-10 min script
- Write `CLIENT_SCENARIO.md`

**Afternoon: Record + Submit**

- Record Loom (with retakes)
- Final code cleanup + setup docs
- Submit

Stretch goals (time permitting):

- Slack webhook notifications
- PR review confidence scoring
- More playbook validation
- One-command `scripts/demo.py`

---

## 7) Tech Stack

| Component     | Technology                         | Why                                 |
| ------------- | ---------------------------------- | ----------------------------------- |
| Orchestrator  | Python 3.11+                       | Readable, async-friendly automation |
| HTTP Client   | `aiohttp`                          | Async parallel API management       |
| Data models   | `pydantic`                         | Validation/serialization/settings   |
| CLI           | `click`                            | Clean CLI UX for demo               |
| Dashboard     | Next.js 14+ + shadcn/ui + Recharts | Polished enterprise UI              |
| State bridge  | `state.json`                       | Simple Python->Next.js integration  |
| Notifications | Slack webhook (stretch)            | Optional alerting surface           |

---

## 8) Verification Plan

1. Mock pipeline test: ingest -> plan -> dispatch -> poll -> `state.json` -> dashboard.
2. API smoke test: verify real key with `POST /v1/sessions` and `GET /v1/sessions/{id}`.
3. Playbook validation: run minimum 3 core playbooks against mock repos, verify PR correctness.
4. Dashboard test: verify auto-refresh and session progress rendering.
5. Hybrid demo test: run 5 real + 10 mock sessions, verify aggregate tracking.
6. Demo dry-run: validate timing and narrative for Loom.

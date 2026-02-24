# CLAUDE.md — Project Brain for Coding Subagents

## Project Overview

This is a take-home project for **Cognition** (makers of Devin, an AI coding agent). We're building a **Security Remediation Orchestrator** that demonstrates how Devin's parallel agent capabilities can systematically remediate security findings at enterprise scale.

**Client scenario**: Coupang (Korea's largest e-commerce platform) has 2,000+ security findings across 600+ microservices after a data breach. Our orchestrator ingests findings from a CSV, categorizes and prioritizes them, dispatches parallel Devin sessions (each with a finding-specific playbook), monitors progress via structured output, and displays everything in a real-time dashboard.

**Deliverables**: Working automation (orchestrator + dashboard) + 5-10 min Loom video demo.

## Architecture

```
CSV Input → Python Orchestrator → Devin API (parallel sessions) → PRs on GitHub
                    ↓
              state.json
                    ↓
         Next.js Dashboard (reads state.json)
```

- **Python orchestrator** (`orchestrator/`): Handles CSV ingestion, finding prioritization, wave-based Devin session dispatch, structured output polling, and state persistence.
- **Next.js dashboard** (`dashboard/`): Reads `state.json` written by the orchestrator, displays real-time progress with auto-refresh.
- **Playbooks** (`playbooks/`): `.devin.md` templates that tell Devin exactly how to remediate each finding type.
- **Sample data** (`sample_data/`): Demo CSV with ~20 findings across 3 mock repos.
- **Mock layer** (`mock/`): Simulates Devin API responses for development/testing without consuming ACUs.

## Tech Stack — MUST USE

| Component     | Technology                                                     | Notes                                            |
| ------------- | -------------------------------------------------------------- | ------------------------------------------------ |
| Orchestrator  | **Python 3.11+**                                               | All orchestrator code must be Python             |
| Async HTTP    | **aiohttp**                                                    | For parallel Devin API calls                     |
| Data models   | **pydantic v2**                                                | All data models use Pydantic BaseModel           |
| Settings      | **pydantic-settings**                                          | Config from env vars / `.env` file               |
| CLI           | **click**                                                      | CLI entry point with subcommands                 |
| Dashboard     | **Next.js 14+ (App Router)**                                   | NOT Pages Router                                 |
| UI components | **shadcn/ui**                                                  | Use shadcn components (Card, Table, Badge, etc.) |
| Styling       | **Tailwind CSS**                                               | No custom CSS files unless absolutely necessary  |
| Charts        | **Recharts** (if needed)                                       | For any data visualization                       |
| Fonts         | **Baskerville** (serif) for titles/headers, **Inter** for body | See Design System below                          |
| State bridge  | **state.json** file                                            | Python writes, Next.js reads                     |

## Design System — Dashboard UI

The dashboard must follow this aesthetic (inspired by a previous project):

- **Typography**: Baskerville (serif/italic) for the app logo, page titles, and section headers. Inter/sans-serif for body text, table content, labels, stats, and all other text.
- **Color palette**: White/off-white background (`#FFFFFF` or `#FAFAFA`). Black text (`#000000` or `#1A1A1A`). Green badges for completed/success (`emerald-100`/`emerald-700`). Red/pink badges for failed (`red-100`/`red-700`). Subtle gray borders on cards (`border-gray-200`). Minimal accent colors — clean, enterprise-grade.
- **Layout**: Left sidebar navigation (icon + text labels) with main content area. Cards use thin rounded borders (`border border-gray-200 rounded-lg`), NOT heavy shadows. Tables are clean with subtle row separators. Generous whitespace and padding.
- **Status badges**: Small rounded pill badges — green for completed/success, amber/yellow for in-progress/working, red for failed, gray for pending.
- **Cards**: 4 summary stat cards in a row. Large Baskerville number, small label above, optional sub-stats below a thin divider line.

## Rules for All Agents

### Code Quality

1. **Type everything**. Python: use type hints on all function signatures. TypeScript: strict mode, no `any`.
2. **Pydantic for all data models**. No raw dicts for structured data in the Python orchestrator.
3. **Async/await** for all Devin API interactions. The orchestrator uses `asyncio` for parallel session dispatch.
4. **Error handling**: Wrap all Devin API calls in try/except. Log errors, don't crash. Sessions can fail — the orchestrator must be resilient.
5. **No hardcoded secrets**. API keys come from environment variables via `config.py`. Use `.env` file locally.

### File Organization

6. **Follow the directory structure exactly** as defined in `SPEC.md`. Don't create new directories or rename existing ones without explicit instruction.
7. **One responsibility per file**. Keep modules focused. Don't put parser + normalizer + prioritizer in one file.
8. **Imports**: Use relative imports within the `orchestrator` package. Use absolute imports for external packages.

### Testing

9. **Test your implementation** after finishing. At minimum, verify:
   - Python: The code runs without import errors. CLI commands work.
   - Next.js: The dev server starts. Pages render without errors.
   - Integration: The orchestrator writes `state.json`, the dashboard reads it.
10. **Mock mode must work end-to-end**. Running the orchestrator with `MOCK_MODE=true` should produce realistic `state.json` output that the dashboard can render.

### Devin API

11. **API base URL**: `https://api.devin.ai/v1`
12. **Auth header**: `Authorization: Bearer {DEVIN_API_KEY}`
13. **Key endpoints**:
    - `POST /v1/sessions` — Create session (params: prompt, playbook_id, tags, structured_output_schema, max_acu_limit, idempotent)
    - `GET /v1/sessions/{session_id}` — Get session details (status_enum, structured_output, pull_request)
    - `GET /v1/sessions` — List sessions (params: tags, limit, offset)
    - `POST /v1/sessions/{session_id}/message` — Send message to session
    - `DELETE /v1/sessions/{session_id}` — Terminate session
    - `POST /v1/playbooks` — Create playbook
    - `GET /v1/playbooks` — List playbooks
14. **Session status values**: `working`, `blocked`, `expired`, `finished`, `suspend_requested`, `resume_requested`, `resumed`
15. **Always use `idempotent: true`** when creating sessions to prevent duplicates on retry.
16. **Set `max_acu_limit: 5`** per session (cap at ~75 min) to prevent runaway sessions.

### State Bridge (state.json)

17. The Python orchestrator writes the full run state to `state.json` in the project root on every poll cycle.
18. The Next.js dashboard reads this file via an API route (`/api/status`).
19. `state.json` structure must match the `BatchRun` Pydantic model exactly (serialized via `.model_dump(mode='json')`).
20. The dashboard polls `/api/status` every 5 seconds for auto-refresh.

### Playbooks

21. Playbook files use `.devin.md` extension and live in `playbooks/`.
22. Every playbook must include sections: Overview, Procedure, Specifications, Advice and Pointers, Forbidden Actions.
23. Playbooks must instruct Devin to update structured output after each major step.

## Environment Variables

```env
DEVIN_API_KEY=apk_user_...           # Devin personal API key
MOCK_MODE=true                       # true = use MockDevinClient, false = real API
MAX_PARALLEL_SESSIONS=10             # Max concurrent Devin sessions
MAX_ACU_PER_SESSION=5                # ACU limit per session
POLL_INTERVAL_SECONDS=20             # Structured output poll interval
SESSION_TIMEOUT_MINUTES=90           # Kill stuck sessions after this
MIN_SUCCESS_RATE=0.7                 # Wave gating threshold (70%)
WAVE_SIZE=10                         # Findings per wave
SLACK_WEBHOOK_URL=                   # Optional Slack webhook (stretch goal)
STATE_FILE_PATH=./state.json         # Path to state file

# EXT-1: Live/Hybrid mode
HYBRID_MODE=false                    # Enable hybrid live+mock routing
CONNECTED_REPOS=                     # Comma-separated repo names (e.g., repo1,repo2)

# EXT-3: Client resilience
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_COOLDOWN_SECONDS=30
MAX_RETRIES=3
RETRY_JITTER_MAX_SECONDS=1.0
```

## Current Progress — Batch 3a Complete

All foundation phases (0-8) are complete. Pre-extension foundation applied. **Batch 1 (EXT-1 + EXT-2), Batch 2a (EXT-3 + EXT-6), Batch 2b (EXT-4), and Batch 3a (EXT-5 + EXT-7A) are complete and verified.**

### Foundation Layer (in codebase)
- `orchestrator/models.py`: `RemediationSession` has `data_source: str = "mock"` and `version: int = 0`. `BatchRun` has `data_source: str = "mock"`. `events` uses `Field(default_factory=list)`.
- `orchestrator/config.py`: Has `hybrid_mode`, `connected_repos` (with CSV env parsing via custom pydantic-settings source), `circuit_breaker_threshold`, `circuit_breaker_cooldown_seconds`, `max_retries`, `retry_jitter_max_seconds`.
- `orchestrator/utils.py`: `with_file_lock()` context manager (cross-process, D5 protocol) and `atomic_write_json()`. Lock protocol uses `O_CREAT | O_EXCL` and is compatible with `dashboard/lib/file-lock.ts`.
- `dashboard/lib/types.ts`: `RemediationSession` has `data_source` and `version`. `BatchRun` has `data_source`. New `RunSummary` interface.
- `dashboard/lib/file-lock.ts`: TypeScript file lock matching Python's D5 protocol.
- `dashboard/app/api/status/route.ts`: Deprecated with `X-Deprecated: true` header per D6.

### EXT-1: Live-First Mode (complete)
- `orchestrator/main.py`: CLI supports `--live` (mock_mode=False) and `--hybrid` (mock_mode=False + hybrid_mode=True) flags. Preflight runs inside `_run_pipeline()` (async context). Hybrid mode creates both DevinClient + MockDevinClient.
- `orchestrator/preflight.py` (NEW): Async `preflight_check(client, config, findings)` validates API key, Devin connectivity, playbook file existence, connected_repos in hybrid mode, and finding count.
- `orchestrator/devin/session_manager.py`: `determine_data_source(finding, config)` uses substring matching on `connected_repos` for hybrid routing. `create_remediation_session()` accepts and stores `data_source`.
- `orchestrator/planner/wave_manager.py`: `__init__` accepts `data_source` and optional `mock_client`. `dispatch_wave`, `poll_wave`, `retry_failed` all route per-session to the appropriate client based on `session.data_source`.
- `scripts/validate_state.py` (NEW): Validates state.json structure and consistency.
- `tests/test_preflight.py` (NEW): 11 tests for preflight scenarios.
- `tests/test_data_source.py` (NEW): 7 tests for hybrid routing logic.
- `dashboard/components/data-source-badge.tsx` (NEW): Pill badge for live/mock/hybrid data source display.
- Dashboard shows data source badge on main page and session detail.

### EXT-2: UI Polish (complete)
- `dashboard/lib/theme.tsx` (NEW): ThemeProvider with localStorage persistence and `useTheme()` hook.
- `dashboard/app/theme-script.tsx` (NEW): Anti-flash inline script that applies dark class before React hydration.
- `dashboard/app/layout.tsx`: Wrapped in ThemeProvider, uses `bg-background text-foreground`, title "Coupang Security Remediation | Cognition", favicon from cognition-logo.png.
- `dashboard/components/sidebar.tsx`: Collapsible (w-64 ↔ w-16) with localStorage persistence, Cognition logo, theme toggle (sun/moon), collapse toggle (chevron).
- `dashboard/app/globals.css`: Dark mode CSS variables in oklch color space matching Devin's charcoal palette (~#191919 bg, #1E1E1E cards, rgba(255,255,255,0.08) borders).
- All phase-1 components migrated to semantic color tokens: `overview-cards.tsx`, `status-badge.tsx`, `sessions-table.tsx`, `findings-table.tsx`, `trace-timeline.tsx`, `pr-queue.tsx`, plus all page files.

### EXT-3: Scale & Security Hardening (complete)
- `orchestrator/devin/client.py`: `CircuitBreaker` class (closed/open/half_open states) with `CircuitBreakerOpen` exception. `_RETRYABLE_STATUSES = {429, 500, 502, 503}`. Enhanced `_request` with Retry-After header support (capped at 60s), exponential backoff + jitter (`random.uniform(0, retry_jitter_max)`), circuit breaker integration. `DevinClient.__init__` accepts `max_retries`, `retry_jitter_max`, `circuit_breaker_threshold`, `circuit_breaker_cooldown`.
- `orchestrator/devin/idempotency.py` (NEW): `IdempotencyLedger` class. Key format: `{run_id}-{finding_id}-attempt-{attempt}`. Persists via `atomic_write_json()`. Handles corrupt files gracefully.
- `orchestrator/devin/session_manager.py`: `create_remediation_session()` accepts optional `ledger` and `run_id`. Checks ledger before API call (idempotency hit skips creation), records after success.
- `orchestrator/planner/wave_manager.py`: `__init__` accepts `ledger` and `run_id`, passes to `create_remediation_session`. Interrupt check (`batch_run.status == "interrupted"`) at start of each wave.
- `orchestrator/main.py`: Passes resilience config to `DevinClient`. Creates `IdempotencyLedger` at `runs/<run_id>/idempotency.json`. SIGINT handler for graceful shutdown (sets status to "interrupted", saves state). `_run_pipeline` passes ledger/run_id to `WaveManager`.
- `tests/test_client_resilience.py` (NEW): 17 tests (10 circuit breaker + 7 idempotency).

### EXT-6: Enterprise Extensions — Run History + ROI (complete)
- `orchestrator/monitor/tracker.py`: `ProgressTracker` now accepts `runs_dir` parameter. `save_state()` writes to 3 locations: `runs/<run_id>/state.json` (atomic), `runs/index.json` (with file lock + atomic), and legacy `state.json` (atomic). `_update_index()` upserts run summary into index.
- `orchestrator/main.py`: Passes `runs_dir="./runs"` to ProgressTracker. `status` command checks `runs/index.json` first, falls back to legacy `state.json`. Extracted `_print_status()` helper.
- `dashboard/app/api/runs/route.ts` (NEW): `GET /api/runs` reads `runs/index.json`, returns empty array if missing.
- `dashboard/app/api/runs/[id]/route.ts` (NEW): `GET /api/runs/:id` reads `runs/<id>/state.json`. Path traversal protection via regex `/^[a-zA-Z0-9-]+$/`. Next.js 15 async params.
- `dashboard/lib/use-status.ts`: Added `useRuns()` (polls /api/runs every 10s), `useRunStatus(runId)` (polls /api/runs/:id every 5s), `useLatestRun()` (chains both). Existing `useStatus()` preserved but deprecated.
- `dashboard/app/history/page.tsx` (NEW): Run history table sorted newest-first with status badges and data source badges.
- `dashboard/components/roi-card.tsx` (NEW): ROI card — `hours = successful * 3`, `cost = hours * $80/hr`.
- `dashboard/app/page.tsx`: 5-column grid (4-col OverviewCards + 1-col ROICard). Uses `useLatestRun()`.
- `dashboard/components/sidebar.tsx`: Added "History" nav item with clock icon after Review. Uses `useLatestRun()`.
- All pages migrated from `useStatus()` to `useLatestRun()`: page.tsx, findings/page.tsx, sessions/page.tsx, review/page.tsx, sessions/[id]/page.tsx, sidebar.tsx.

### EXT-4: Memory Layer for Agents (complete)
- `orchestrator/memory/__init__.py` (NEW): Package init.
- `orchestrator/memory/models.py` (NEW): Pydantic models — `MemoryItem` (full narrative, stored as markdown), `MemoryGraph` (metadata-only index), `MemoryGraphEntry` (per-item metadata with relationships), `MemoryRelationship` (same_category, same_service links). All list fields use `Field(default_factory=list)`.
- `orchestrator/memory/store.py` (NEW): `MemoryStore` class — filesystem-backed store with `graph.json` (metadata index, locked + atomic writes) and `items/<item_id>.md` (full markdown). `upsert()` builds `same_category`/`same_service` relationships between entries. `load_graph()` handles corrupt files gracefully.
- `orchestrator/memory/extractor.py` (NEW): `extract_memories(batch_run)` converts terminal sessions (SUCCESS, FAILED, TIMEOUT, BLOCKED) into `MemoryItem` objects. Item ID format: `{run_id}-{finding_id}` (enables cross-run accumulation — the same finding across different runs produces distinct entries). Copies `data_source` from session.
- `orchestrator/memory/retriever.py` (NEW): `retrieve_memories(finding, store)` scores and ranks memories. Scoring hierarchy: category match (10) > service match (5) > zero-relevance gate (if neither matches, return 0.0) > severity match (2) > confidence bonus (high=3, medium=1.5, low=0.5) > live source bonus (2) > success bonus (3) > freshness decay (50% over 30 days). Mock memories include warning note in source citation.
- `orchestrator/devin/session_manager.py`: Added `build_memory_context(finding)` helper that retrieves memories and formats them with source citations. `build_remediation_prompt()` accepts `memory_context` param. `create_remediation_session()` calls `build_memory_context()` before prompt construction.
- `orchestrator/monitor/tracker.py`: Added `extract_and_save_memories()` method to `ProgressTracker` — creates MemoryStore, extracts items, upserts into graph, saves.
- `orchestrator/main.py`: Added `extract-memory` CLI subcommand (reads from latest or specified run, extracts memories, saves to store). Auto-extraction after successful runs in `run` command (wrapped in try/except, non-fatal).
- `tests/test_memory.py` (NEW): 14 tests — 5 extractor (success/failed/pending/working extraction, item_id format), 3 store (save/load graph, save/load item, upsert updates), 6 retriever (category ranking, live preference, mock note, no-match empty, max_results, cross-run accumulation with relationship verification).

### EXT-5: Agentic UI — CSV Upload from Dashboard (complete)
- `dashboard/app/api/runs/route.ts` (MODIFIED): Added `POST` handler alongside existing `GET`. Accepts `multipart/form-data` with `file` (CSV) and optional `wave_size` (1-100, default 5). Validates: file extension (.csv), file size (max 10MB), required columns (9 columns), max 5000 rows. Generates 8-char UUID `run_id`, saves CSV to `runs/<run_id>/findings.csv`, writes `bootstrap.json` lifecycle (starting → started → failed_to_spawn), spawns orchestrator via `child_process.spawn()` with `detached: true` + `proc.unref()`, writes PID. Returns 201.
- `dashboard/components/upload-modal.tsx` (NEW): Drag-and-drop CSV upload modal with file validation, wave size input, loading/error states, SWR cache invalidation via `mutate("/api/runs")` on success. All semantic color tokens for dark mode.
- `dashboard/components/run-selector.tsx` (NEW): Dropdown for switching between runs. Shows run_id, relative time, status badge, data source badge. Controlled component with `selectedRunId`/`onSelect` props. "Latest run (auto)" default option. Click-outside detection.
- `dashboard/app/page.tsx` (MODIFIED): Added "New Run" button that opens upload modal. Integrated RunSelector dropdown. State management: `selectedRunId` state switches between `useLatestRun()` and `useRunStatus(runId)`. Existing 5-col grid layout preserved.
- `dashboard/middleware.ts` (NEW): Security middleware for all `/api/*` routes. Optional bearer auth via `DASHBOARD_API_TOKEN` env var. Per-IP rate limiting (60 req/min). Content-Type validation for POST/PUT/DELETE (allows multipart/form-data + application/json). Origin check for browser requests against `APP_ORIGIN` env var. Matcher: `/api/:path*`.

### EXT-7A: Evaluation Harness + SLO/Ops View (complete)
- `dashboard/lib/types.ts` (MODIFIED): Added `CategoryEvalMetrics` interface (category, total, succeeded, failed, pass_rate, avg_duration_seconds, retry_count, avg_confidence, health), `EvalSummary` interface (run_id, counts per health status, categories array), `OpsMetrics` interface (p50/p95/avg/min/max durations, sessions_per_hour, projected_completion_minutes, ACU estimates, wave progress, elapsed_minutes).
- `dashboard/lib/use-status.ts` (MODIFIED): Added `useEval()` (polls /api/eval every 10s, typed EvalSummary) and `useOps()` (polls /api/ops every 5s, typed OpsMetrics). Existing hooks unchanged.
- `dashboard/app/api/eval/route.ts` (NEW): Computes per-category pass/fail rates, avg duration, retry count, avg confidence, health scoring from latest run. Health thresholds: healthy (>= 80%), degraded (50-79%), critical (< 50%), insufficient_data (< 3 sessions). Sorts by health severity (critical first). Division-by-zero guards on all calculations.
- `dashboard/app/api/ops/route.ts` (NEW): Computes p50/p95 percentiles from sorted durations, throughput (sessions/hr), projected remaining time, ACU burn rate estimates (avg_duration_minutes / 15 per session), wave progress. Edge guards: `elapsedHours > 0.01`, null for insufficient data, `Math.max(0, ...)` for projections.
- `dashboard/app/eval/page.tsx` (NEW): Critical alert banner when any category is critical. 4 summary cards (Total, Healthy, Degraded, Critical). Category table with pass rate (color-coded), avg duration, retries, confidence, HealthBadge. Edge guards: "---" for null, "(low sample)" annotation for insufficient_data.
- `dashboard/app/ops/page.tsx` (NEW): Status bar (run ID, status, elapsed, wave progress). 5 duration cards (p50, p95, avg, min, max). Throughput section with progress bar. ACU budget section with burn rate. Alert badges: Slow p95 (> 600s), ACU overburn, Long ETA (> 120min). All formatters handle null with "---" or "Calculating...".
- `dashboard/components/health-badge.tsx` (NEW): Reusable badge — healthy (emerald), degraded (amber), critical (red), insufficient_data (gray/muted). Matches existing badge patterns (ring-1, ring-inset, rounded-full). Dark mode variants.
- `dashboard/components/sidebar.tsx` (MODIFIED): Appended "Eval" and "Ops" nav items after History at end of navItems array. Both have SVG icons for collapsed/expanded states. Existing items unchanged.

### Important Notes for Subagents
- **Do NOT use bare mutable defaults** in Pydantic models. Always use `Field(default_factory=list)` or `Field(default_factory=dict)`.
- **Lock protocol**: When writing to `runs/index.json` or per-run `state.json` (when HITL is active), use `with_file_lock()` (Python) or `withFileLock()` (TypeScript).
- **Atomic writes**: All shared JSON file writes must use `atomic_write_json()` or the temp+rename pattern.
- **`/api/status` is deprecated**: New code must use `GET /api/runs` and `GET /api/runs/:id`. See D6 in EXTENSIONS_PLAN.md.
- **Dark mode**: All new dashboard components must use semantic color tokens (`bg-background`, `text-foreground`, `border-border`, `bg-card`, `text-muted-foreground`, etc.) — never hardcode `bg-white`, `text-gray-*`, or `border-gray-*`.
- **Sidebar nav**: When adding nav items, append at the end of the `navItems` array to reduce merge conflicts. Include both `icon` and `label` properties for collapsed/expanded states.
- **Data source**: All new session-related displays should show `data_source` when relevant. Use `DataSourceBadge` component.

### Next Steps
See `EXTENSIONS_PLAN.md` for the full extension plan. Batch 3b (EXT-7B HITL Approval + Per-Service Playbook Adaptation) is the final batch.

## How to Run

```bash
# Python orchestrator
cd orchestrator
pip install -e .
python -m orchestrator.main run ../sample_data/findings.csv

# Next.js dashboard (separate terminal)
cd dashboard
npm install
npm run dev
# Open http://localhost:3000
```

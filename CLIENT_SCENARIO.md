# Client Scenario: Coupang Security Remediation

## Executive Summary

Coupang faces mounting regulatory pressure from Korea's Personal Information Protection Act (PIPA) amendments following a major data breach that exposed 33.7 million customer records. With 2,000+ open security findings across 600+ microservices and an FSS audit expected in Q2 2026, Coupang's engineering team cannot clear the backlog in time through manual remediation alone. Devin's parallel agent capabilities can systematically remediate the full finding backlog in approximately three weeks — freeing engineering capacity, meeting the audit deadline, and reducing potential fine exposure of up to $2.6 billion.

## Discovery — What We Found

### Company Profile

- **Coupang**: Korea's largest e-commerce platform ("the Amazon of Korea"), publicly traded on NYSE
- **600+ microservices** across a polyglot codebase: Java/Spring Boot, Python/Flask, Go, TypeScript/Express, Kotlin
- AWS-native infrastructure with mature CI/CD pipelines and established code review practices

### The Incident

- **November 2025**: A data breach exposed **33.7 million customer records**, including names, addresses, payment tokens, and order histories
- Multiple attack vectors exploited simultaneously: vulnerable third-party dependencies, insufficient data access controls, and PII exposure in application logs
- Incident response stabilized the immediate threat, but the underlying codebase vulnerabilities remain unaddressed

### The Backlog

- **2,000+ open security findings** surfaced by SonarQube, Snyk, and CodeQL scans
- Breakdown by category: dependency vulnerabilities (40%), code-level patterns such as SQL injection and XSS (30%), PII and data protection gaps (20%), configuration and secrets management (10%)
- Current bottleneck: platform engineers are fully allocated to reliability work and holiday-season feature delivery

### Regulatory Pressure

- Korean Personal Information Protection Act (PIPA) amendments advancing through the National Assembly
- Proposed fines rising to **10% of annual revenue** — Coupang's 2024 revenue of approximately $26 billion implies potential exposure of **$2.6 billion**
- CEO personal criminal liability for demonstrated negligence in data protection
- **Financial Supervisory Service (FSS) audit expected Q2 2026** — the hard deadline

## Client Pain Statement

> "We just went through a major data incident. Our CISO's security team has identified 2,000+ security findings across our 600+ microservices — vulnerable dependencies, hardcoded secrets, SQL injection patterns, insufficient data access logging, missing encryption, and PII exposure in logs. Our scanners flag dozens of new issues weekly. But our platform engineers are heads-down on reliability and the upcoming holiday season. We need to systematically remediate these findings before the FSS audit in Q2, or we face fines that could be 10% of our annual revenue."

## Proposed Solution — Devin-Powered Remediation

### How It Works

The remediation pipeline uses wave-based parallel agent orchestration to process findings at scale:

1. **Ingest** — Coupang's security team exports findings as a CSV from their existing scanner dashboards (SonarQube, Snyk, CodeQL). The dashboard also supports direct CSV upload from the browser, removing the need for CLI access.
2. **Triage** — The orchestrator parses, deduplicates, and scores each finding by severity, category, and affected service to establish remediation priority. Service-specific configuration (test commands, branch prefixes, deployment notes) is applied automatically.
3. **Plan** — Findings are grouped into priority-ordered waves, with the highest-severity issues addressed first. The orchestrator loads relevant memories from previous remediation runs to inform fix strategies.
4. **Dispatch** — Each finding is assigned to a parallel Devin session equipped with a finding-specific playbook that defines the exact remediation procedure. Sessions are created with idempotency protection and circuit-breaker-guarded API calls.
5. **Monitor** — A real-time dashboard provides visibility into session progress, structured output from each agent, and a live event timeline that tracks every stage transition (analyzing, fixing, testing, creating PR, completed).
6. **Review** — Every Devin session produces a pull request. The dashboard includes a human-in-the-loop review workflow where the CISO team can approve or reject each fix with a reason, creating an audit trail.
7. **Learn** — After each run, the orchestrator extracts memories from completed sessions — fix approaches, failure patterns, confidence levels — and stores them in a persistent knowledge graph. Future runs retrieve relevant memories to improve fix quality over time.

### Playbook Categories

Each finding type is addressed by a specialized playbook that guides Devin through the remediation:

- **Dependency Vulnerability** — Identifies the vulnerable package, upgrades to the patched version, resolves breaking API changes, and verifies the build passes.
- **SQL Injection** — Locates raw query construction patterns and replaces them with parameterized queries or ORM-based alternatives.
- **Hardcoded Secrets** — Detects secrets embedded in source code, migrates them to a secrets manager or environment variables, and removes the plaintext values from version history.
- **PII Logging** — Finds personally identifiable information written to application logs and applies redaction or filtering to prevent data leakage.
- **Missing Encryption** — Identifies sensitive data stored or transmitted without encryption and applies appropriate encryption at rest or in transit.
- **Access Logging** — Adds structured audit logging to data access paths that lack traceability, ensuring compliance with regulatory record-keeping requirements.

### Safety Guardrails

- **Isolation**: One finding per Devin session — each remediation is scoped and independent
- **Wave gating**: If the success rate within a wave drops below 70%, the pipeline pauses automatically for human review before proceeding
- **Cost controls**: Every session is capped at 5 ACUs (approximately 75 minutes) to prevent runaway costs
- **Idempotency**: A per-run ledger prevents duplicate session creation on retry or restart, keyed by run ID, finding ID, and attempt number
- **Circuit breaker**: The Devin API client implements a circuit breaker (closed/open/half-open) that halts requests after consecutive failures, preventing cascading errors during API outages
- **Retry with backoff**: Transient API errors (429, 500-503) are retried with exponential backoff, jitter, and Retry-After header support
- **Graceful shutdown**: SIGINT saves the current run state immediately, allowing the pipeline to resume from where it stopped
- **Mandatory review**: Every pull request requires approval from both the CISO team and the service owner before merge. The dashboard supports approve/reject actions with reviewer attribution and timestamped audit events.
- **Forbidden actions**: Playbooks explicitly prohibit committing directly to main, disabling tests, or modifying CI/CD configuration

## Platform Capabilities

### Real-Time Dashboard

The remediation dashboard provides eight views designed for different stakeholders:

1. **Overview** — Summary cards showing total findings, active sessions, PRs created, success rate, and ROI metrics. At-a-glance status for executive check-ins.
2. **Findings** — The complete finding inventory with filtering by severity, category, and service. Track which findings are pending, in progress, or resolved.
3. **Sessions** — Live session list with drill-down to individual session detail: current status, Devin's progress through the playbook steps, structured output (fix approach, confidence, files modified, tests passed), and a timestamped event timeline showing every stage transition.
4. **Review** — The pull request queue with approve/reject actions, reviewer attribution, and confidence scores. Human-in-the-loop governance for every remediation.
5. **History** — Run history across all remediation campaigns, with per-run summaries (status, finding counts, success rate, data source).
6. **Evaluation** — Per-category health metrics: pass rate, average duration, retry count, and confidence distribution. Health badges (healthy/degraded/critical) surface categories needing playbook tuning.
7. **Operations** — Operational metrics: p50/p95 session duration, throughput (sessions per hour), ACU burn rate and budget remaining, projected completion time. Alert badges for anomalies.

### Web-Based Run Trigger

The dashboard supports starting remediation runs directly from the browser:

- Upload a CSV of findings via drag-and-drop
- Configure wave size and execution mode (Live, Mock, or Hybrid)
- The orchestrator spawns as a background process and the dashboard tracks progress in real time
- No CLI access required — designed for security team operators

### Hybrid Execution Mode

For phased rollouts, the orchestrator supports hybrid routing:

- **Live mode**: All findings dispatch to real Devin sessions against production repositories
- **Mock mode**: Simulated sessions for testing and demonstration without consuming API resources
- **Hybrid mode**: Findings whose service matches a connected repository list route to live Devin; all others use simulated sessions. This enables incremental onboarding — connect one service at a time.

### Cross-Run Memory

The orchestrator builds a persistent knowledge graph from completed remediation sessions:

- After each run, successful fix approaches, failure patterns, and confidence levels are extracted and stored as markdown documents with a metadata index
- Before dispatching a new session, the orchestrator retrieves relevant memories (ranked by category match, service match, confidence, freshness, and data source) and injects them into the Devin prompt as prior context
- Live-mode memories are preferred over mock-mode memories, with explicit source citations
- This enables the system to improve over time — learning from both successes and failures

### Structured Output

Each Devin session continuously reports: finding identifier, remediation status, progress percentage, current step, fix approach taken, files modified, tests passed and added, pull request URL, confidence level, and error messages. This structured output powers the dashboard, the evaluation metrics, and the audit trail.

## Validation and Rollout Plan

| Phase | Timeline | Scope | Success Criteria |
|-------|----------|-------|------------------|
| **Pilot** | Weeks 1--2 | 50 highest-severity findings across 10 services | At least 80% auto-remediation rate, all PRs pass CI, CISO team approval on every merge |
| **Scale** | Weeks 3--8 | Full 2,000-finding remediation with 10 parallel sessions per wave | Backlog cleared before FSS audit deadline |
| **Ongoing** | Week 9+ | CI-connected: new scanner findings automatically trigger Devin sessions | Security backlog never grows; continuous compliance posture maintained |

### Enterprise Deployment

- **Data residency**: Customer-hosted VPC deployment or dedicated SaaS instance with PrivateLink to satisfy PIPA data residency requirements
- **Access control**: Role-based access with scoped service users — CISO team with view-level organization access, engineers with session management permissions
- **Audit trail**: Full session logs, review decisions with reviewer attribution, and timestamped event timelines for every remediation action — providing the traceability required for FSS compliance reporting
- **Operational monitoring**: Built-in evaluation and operations dashboards surface system health without requiring external observability tooling

## ROI Analysis

### Without Devin

- 2,000 findings at an average of 3 hours per remediation = **6,000 engineer-hours**
- At $80/hour fully loaded cost: **$480,000 in direct engineering spend**
- Approximately **15 FTE-months** diverted from reliability and product work
- Estimated timeline: 4--6 months — likely missing the FSS audit deadline

### With Devin

- 10 parallel Devin sessions processing approximately 100 findings per day
- Full 2,000-finding backlog completed in **approximately 3 weeks** of wall-clock time
- Human review effort: roughly 15 minutes per PR across 2,000 PRs = **500 engineer-hours**
- **Net savings: 5,500+ engineer-hours and 12+ FTE-months freed** for reliability and product delivery
- **Meets the FSS audit deadline with margin to spare**

### Regulatory Risk Mitigation

- Potential PIPA fine exposure: up to **$2.6 billion** (10% of annual revenue)
- Total remediation investment: a fraction of 1% of that exposure
- Demonstrating a systematic, auditable remediation effort is itself a significant mitigating factor in regulatory proceedings

## Next Steps

1. **Technical deep-dive** — Schedule a working session with Coupang's security engineering team to review scanner output formats and repository access
2. **Pilot launch** — Connect Devin to 10 representative services and run the 50 highest-severity findings with live playbooks
3. **Pilot review** — Evaluate results, tune playbooks based on Coupang's codebase patterns, and finalize the full-scale rollout plan
4. **Full-scale remediation** — Scale to the complete 2,000-finding backlog with integration into Coupang's CI/CD pipelines

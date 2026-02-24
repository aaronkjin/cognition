from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import OrchestratorConfig
from orchestrator.models import (
    Finding,
    FindingCategory,
    RemediationSession,
    SessionStatus,
)

logger = logging.getLogger(__name__)

_SERVICE_OVERRIDES_PATH = Path("service_overrides.json")


# JSON Schema Draft 7 for the structured output that every Devin session reports
REMEDIATION_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "finding_id": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["analyzing", "fixing", "testing", "creating_pr", "completed", "failed"],
        },
        "progress_pct": {"type": "integer", "minimum": 0, "maximum": 100},
        "current_step": {"type": "string"},
        "fix_approach": {"type": ["string", "null"]},
        "files_modified": {"type": "array", "items": {"type": "string"}},
        "tests_passed": {"type": ["boolean", "null"]},
        "tests_added": {"type": "integer"},
        "pr_url": {"type": ["string", "null"]},
        "error_message": {"type": ["string", "null"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["finding_id", "status", "progress_pct", "current_step"],
}


def load_service_overrides() -> dict[str, Any]:
    """Load service overrides from service_overrides.json. Returns empty dict on failure."""
    try:
        if _SERVICE_OVERRIDES_PATH.exists():
            return json.loads(_SERVICE_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load service overrides: %s", exc)
    return {}


def build_remediation_prompt(
    finding: Finding,
    memory_context: str | None = None,
    service_overrides: dict[str, Any] | None = None,
    run_id: str = "",
) -> str:
    """Construct the session prompt from a Finding, optionally enriched with memory and service overrides."""
    line = str(finding.line_number) if finding.line_number is not None else "N/A"
    cwe = finding.cwe_id or "N/A"

    prompt = f"""## Security Remediation Task

**Run ID**: {run_id}
**Finding ID**: {finding.finding_id}
**Service**: {finding.service_name}
**Category**: {finding.category.value}
**Severity**: {finding.severity.value}
**File**: {finding.file_path}
**Line**: {line}
**CWE**: {cwe}

**Title**: {finding.title}

**Description**: {finding.description}
"""

    if finding.category == FindingCategory.DEPENDENCY_VULNERABILITY:
        dep = finding.dependency_name or "N/A"
        cur_ver = finding.current_version or "N/A"
        fix_ver = finding.fixed_version or "N/A"
        prompt += f"""
**Dependency**: {dep}
**Current Version**: {cur_ver}
**Fixed Version**: {fix_ver}
"""

    prompt += f"""
## Instructions
1. Clone the repository at {finding.repo_url}
2. Fix the vulnerability described above following the playbook instructions
3. Update structured output after each major step (analyzing, fixing, testing, creating_pr, completed)
4. Run existing tests and ensure they pass
5. Create a pull request with the fix on a new branch
"""

    # Add service overrides section if applicable
    if service_overrides:
        overrides = service_overrides.get(finding.service_name)
        if overrides:
            prompt += f"""
## Service-Specific Instructions ({finding.service_name})
- **Test Command**: {overrides.get('test_command', 'N/A')}
- **Branch Prefix**: {overrides.get('branch_prefix', 'security/fix')}
- **Deployment Notes**: {overrides.get('deployment_notes', 'Standard deployment.')}

{overrides.get('custom_instructions', '')}
"""

    if memory_context:
        prompt += f"""
## Prior Remediation Knowledge
The following context is from previous remediation sessions for similar findings.
Use this as reference but verify applicability to the current codebase.

{memory_context}
"""

    return prompt


def build_memory_context(
    finding: Finding, memory_dir: str = "orchestrator/memory"
) -> str | None:
    """Build memory context string for a finding from the memory store.

    Returns None if no relevant memories found.
    """
    try:
        from orchestrator.memory.retriever import retrieve_memories
        from orchestrator.memory.store import MemoryStore

        store = MemoryStore(memory_dir)
        memories = retrieve_memories(finding, store, max_results=3)
        if not memories:
            return None

        parts: list[str] = []
        for mem in memories:
            parts.append(f"### {mem['source_note']}\n\n{mem['content']}")

        return "\n---\n\n".join(parts)
    except Exception as exc:
        logger.warning(
            "Could not retrieve memories for %s: %s", finding.finding_id, exc
        )
        return None


def determine_data_source(
    finding: Finding,
    config: OrchestratorConfig,
) -> str:
    """Determine whether a finding should use live or mock mode.

    In hybrid mode, findings whose service_name appears in connected_repos
    (substring match) use live mode; all others fall back to mock.
    In non-hybrid mode, returns based on mock_mode flag.
    """
    if config.mock_mode:
        return "mock"
    if not config.hybrid_mode:
        return "live"
    # Hybrid: check if service repo is connected
    for repo in config.connected_repos:
        if finding.service_name in repo or repo in finding.service_name:
            logger.info(
                "Hybrid routing: %s → live (matched repo %s)",
                finding.finding_id, repo,
            )
            return "live"
    logger.info("Hybrid routing: %s → mock (no repo match)", finding.finding_id)
    return "mock"


async def create_remediation_session(
    client: Any,  # DevinClient or MockDevinClient
    session: RemediationSession,
    config: OrchestratorConfig,
    data_source: str = "mock",
    ledger: Any | None = None,  # IdempotencyLedger
    run_id: str = "",
) -> RemediationSession:
    """Create a Devin session for a remediation task."""
    try:
        # Check idempotency ledger first
        if ledger is not None and run_id:
            key = ledger.make_key(run_id, session.finding.finding_id, session.attempt)
            existing = ledger.lookup(key)
            if existing:
                logger.info(
                    "Idempotency hit: %s already has session %s",
                    key, existing["session_id"],
                )
                session.session_id = existing["session_id"]
                session.status = SessionStatus.DISPATCHED
                session.data_source = data_source
                return session

        overrides = load_service_overrides()
        memory_ctx = build_memory_context(session.finding)
        prompt = build_remediation_prompt(
            session.finding,
            memory_context=memory_ctx,
            service_overrides=overrides,
            run_id=run_id,
        )
        tags = [
            f"wave-{session.wave_number}",
            session.finding.category.value,
            session.finding.service_name,
        ]
        playbook_id = session.playbook_id if session.playbook_id else None

        response = await client.create_session(
            prompt=prompt,
            playbook_id=playbook_id,
            tags=tags,
            structured_output_schema=REMEDIATION_OUTPUT_SCHEMA,
            max_acu_limit=config.max_acu_per_session,
            idempotent=True,
        )

        session.session_id = response["session_id"]
        session.devin_url = response.get("url")
        session.status = SessionStatus.DISPATCHED
        session.data_source = data_source
        session.created_at = datetime.now(timezone.utc)

        # Record in idempotency ledger after successful creation
        if ledger is not None and run_id:
            key = ledger.make_key(run_id, session.finding.finding_id, session.attempt)
            ledger.record(
                key,
                session.session_id,
                session.created_at.isoformat() if session.created_at else "",
            )

        logger.info(
            "Created session %s for finding %s",
            session.session_id,
            session.finding.finding_id,
        )
    except Exception as exc:
        logger.error(
            "Failed to create session for finding %s: %s",
            session.finding.finding_id,
            exc,
        )
        session.status = SessionStatus.FAILED
        session.error_message = str(exc)

    return session


_STATUS_MAP: dict[str, SessionStatus] = {
    "working": SessionStatus.WORKING,
    "finished": SessionStatus.SUCCESS,
    "blocked": SessionStatus.BLOCKED,
    "expired": SessionStatus.TIMEOUT,
    # Transitional states — keep polling
    "suspend_requested": SessionStatus.WORKING,
    "resume_requested": SessionStatus.WORKING,
    "resumed": SessionStatus.WORKING,
}


def interpret_session_status(api_response: dict[str, Any]) -> tuple[SessionStatus, str | None, str | None]:
    """Map Devin API response to our SessionStatus enum.

    Handles real Devin API semantics:
    - 'blocked' with a PR means Devin finished and is waiting for human approval → SUCCESS
    - 'blocked' without a PR means Devin is stuck and needs help → BLOCKED
    - Unknown status_enum values are treated as WORKING (keep polling) rather than FAILED

    Returns:
        Tuple of (status, pr_url, error_message).
    """
    status_enum = api_response.get("status_enum", "")

    pr_url: str | None = None
    pull_request = api_response.get("pull_request")
    if pull_request and isinstance(pull_request, dict):
        pr_url = pull_request.get("url")

    error_message: str | None = None
    structured_output = api_response.get("structured_output")
    if structured_output and isinstance(structured_output, dict):
        error_message = structured_output.get("error_message")

    # 'blocked' + PR = Devin created the PR and is waiting for approval → SUCCESS
    if status_enum == "blocked" and pr_url:
        logger.info("Session blocked with PR present — treating as success")
        return SessionStatus.SUCCESS, pr_url, error_message

    # Map known statuses; default to WORKING for unknown values to keep polling
    status = _STATUS_MAP.get(status_enum, SessionStatus.WORKING)
    if status_enum and status_enum not in _STATUS_MAP:
        logger.warning(
            "Unknown Devin status_enum '%s' — treating as WORKING (will keep polling)",
            status_enum,
        )

    return status, pr_url, error_message

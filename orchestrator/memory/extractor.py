from __future__ import annotations

import logging
from datetime import datetime, timezone

from orchestrator.memory.models import MemoryItem
from orchestrator.models import BatchRun, RemediationSession, SessionStatus

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {
    SessionStatus.SUCCESS,
    SessionStatus.FAILED,
    SessionStatus.TIMEOUT,
    SessionStatus.BLOCKED,
}


def extract_memories(batch_run: BatchRun) -> list[MemoryItem]:
    """Extract memory items from all terminal sessions in a batch run.

    Only extracts from sessions that have reached a terminal state
    (success, failed, timeout, blocked).
    """
    items: list[MemoryItem] = []

    for wave in batch_run.waves:
        for session in wave.sessions:
            if session.status not in _TERMINAL_STATUSES:
                continue

            item = _session_to_memory(session, batch_run.run_id)
            if item is not None:
                items.append(item)

    logger.info("Extracted %d memory items from run %s", len(items), batch_run.run_id)
    return items


def _session_to_memory(session: RemediationSession, run_id: str) -> MemoryItem | None:
    """Convert a completed RemediationSession to a MemoryItem."""
    finding = session.finding
    so = session.structured_output or {}

    outcome = "success" if session.status == SessionStatus.SUCCESS else "failed"

    return MemoryItem(
        item_id=f"{run_id}-{finding.finding_id}",
        finding_id=finding.finding_id,
        category=finding.category.value,
        service_name=finding.service_name,
        severity=finding.severity.value,
        title=finding.title,
        data_source=session.data_source,
        outcome=outcome,
        confidence=so.get("confidence"),
        fix_approach=so.get("fix_approach"),
        files_modified=so.get("files_modified", []),
        error_message=session.error_message or so.get("error_message"),
        tests_passed=so.get("tests_passed"),
        tests_added=so.get("tests_added", 0),
        pr_url=session.pr_url,
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

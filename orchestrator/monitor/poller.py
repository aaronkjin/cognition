from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from orchestrator.config import OrchestratorConfig
from orchestrator.devin.session_manager import interpret_session_status
from orchestrator.models import RemediationSession, SessionStatus

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = {SessionStatus.DISPATCHED, SessionStatus.WORKING, SessionStatus.BLOCKED}

_TERMINAL_STATUSES = {
    SessionStatus.SUCCESS,
    SessionStatus.FAILED,
    SessionStatus.TIMEOUT,
}

# BLOCKED is NOT terminal — Devin may still be working or waiting for input.
# If blocked + PR, interpret_session_status already maps to SUCCESS.


async def poll_session(
    client: Any,  # DevinClient or MockDevinClient
    session: RemediationSession,
) -> RemediationSession:
    """Poll a single session and update its state.

    On API failure, logs the error and returns the session unchanged.
    """
    try:
        response = await client.get_session(session.session_id)

        # Update structured output
        structured_output = response.get("structured_output")
        if structured_output is not None:
            session.structured_output = structured_output

        # Interpret the status
        new_status, pr_url, error_message = interpret_session_status(response)

        if new_status in _TERMINAL_STATUSES:
            session.status = new_status
            session.completed_at = datetime.now(timezone.utc)
            if pr_url:
                session.pr_url = pr_url
            if error_message:
                session.error_message = error_message
        elif new_status == SessionStatus.WORKING:
            session.status = SessionStatus.WORKING
            if pr_url:
                session.pr_url = pr_url

    except Exception as exc:
        logger.error(
            "Failed to poll session %s: %s",
            session.session_id,
            exc,
        )

    return session


async def poll_active_sessions(
    client: Any,  # DevinClient or MockDevinClient
    sessions: list[RemediationSession],
    tracker: Any,  # ProgressTracker (use Any to avoid circular import)
    config: OrchestratorConfig,
) -> list[RemediationSession]:
    """Poll all active sessions once and return still-active ones.

    Also checks for timeouts based on config.session_timeout_minutes.
    """
    now = datetime.now(timezone.utc)
    timeout_seconds = config.session_timeout_minutes * 60
    still_active: list[RemediationSession] = []

    active_sessions = [s for s in sessions if s.status in _ACTIVE_STATUSES]

    for session in active_sessions:
        old_status = session.status

        # Capture previous structured output stage for progress tracking
        old_so = session.structured_output
        old_stage = old_so.get("status") if old_so and isinstance(old_so, dict) else None

        # Check for timeout before polling
        if session.created_at is not None:
            elapsed = (now - session.created_at).total_seconds()
            if elapsed > timeout_seconds:
                session.status = SessionStatus.TIMEOUT
                session.error_message = "Session timed out"
                session.completed_at = now
                tracker.update_session(session)
                tracker.add_event(
                    "session_failed",
                    f"Session {session.finding.finding_id} timed out",
                    {
                        "finding_id": session.finding.finding_id,
                        "session_id": session.session_id,
                        "reason": "timeout",
                    },
                )
                continue

        # Poll the session
        session = await poll_session(client, session)

        # Emit progress event when structured output stage changes
        new_so = session.structured_output
        new_stage = new_so.get("status") if new_so and isinstance(new_so, dict) else None
        if new_stage and new_stage != old_stage:
            step_msg = (
                new_so.get("current_step", "")
                if new_so and isinstance(new_so, dict)
                else ""
            )
            progress_pct = (
                new_so.get("progress_pct", 0)
                if new_so and isinstance(new_so, dict)
                else 0
            )
            # Human-readable stage label
            stage_labels = {
                "analyzing": "Analyzing vulnerability",
                "fixing": "Applying fix",
                "testing": "Running tests",
                "creating_pr": "Creating pull request",
                "completed": "Completed",
                "failed": "Failed",
            }
            label = stage_labels.get(new_stage, new_stage)
            tracker.add_event(
                "session_progress",
                f"{session.finding.finding_id}: {label}",
                {
                    "finding_id": session.finding.finding_id,
                    "session_id": session.session_id,
                    "stage": new_stage,
                    "progress_pct": progress_pct,
                    "current_step": step_msg,
                },
            )

        # Check if status changed
        if session.status != old_status:
            tracker.update_session(session)

            if session.status == SessionStatus.SUCCESS:
                tracker.add_event(
                    "session_completed",
                    f"Session {session.finding.finding_id} completed successfully",
                    {
                        "finding_id": session.finding.finding_id,
                        "session_id": session.session_id,
                        "pr_url": session.pr_url,
                    },
                )
            elif session.status in _TERMINAL_STATUSES:
                tracker.add_event(
                    "session_failed",
                    f"Session {session.finding.finding_id} failed with status {session.status.value}",
                    {
                        "finding_id": session.finding.finding_id,
                        "session_id": session.session_id,
                        "error": session.error_message,
                    },
                )

        # Collect still-active sessions
        if session.status in _ACTIVE_STATUSES:
            still_active.append(session)

    tracker.save_state()
    return still_active

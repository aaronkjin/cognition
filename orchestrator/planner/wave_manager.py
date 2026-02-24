from __future__ import annotations

import asyncio
import logging
from typing import Any

from orchestrator.config import OrchestratorConfig
from orchestrator.devin.session_manager import create_remediation_session
from orchestrator.models import BatchRun, RemediationSession, SessionStatus, Wave
from orchestrator.monitor.poller import poll_active_sessions
from orchestrator.monitor.tracker import ProgressTracker

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {
    SessionStatus.SUCCESS,
    SessionStatus.FAILED,
    SessionStatus.TIMEOUT,
}

_RETRIABLE_STATUSES = {
    SessionStatus.FAILED,
    SessionStatus.TIMEOUT,
}

# BLOCKED is active — Devin may still create a PR while in 'blocked' state.
# interpret_session_status will promote blocked+PR to SUCCESS.
_ACTIVE_STATUSES = {
    SessionStatus.DISPATCHED,
    SessionStatus.WORKING,
    SessionStatus.BLOCKED,
}


class WaveManager:
    """Orchestrates wave-based dispatch of Devin remediation sessions."""

    def __init__(
        self,
        client: Any,  # DevinClient or MockDevinClient
        config: OrchestratorConfig,
        tracker: ProgressTracker,
        data_source: str = "mock",
        mock_client: Any | None = None,
        ledger: Any | None = None,
        run_id: str = "",
    ) -> None:
        self._client = client
        self._config = config
        self._tracker = tracker
        self._data_source = data_source
        self._mock_client = mock_client
        self._ledger = ledger
        self._run_id = run_id

    async def execute_run(self, batch_run: BatchRun) -> BatchRun:
        """Execute all waves in a batch run."""
        # Drain any stale sessions from previous runs before starting
        await self._drain_stale_sessions()

        for wave in batch_run.waves:
            # Check for interrupt before starting next wave
            if batch_run.status == "interrupted":
                logger.info("Run interrupted, stopping dispatch")
                break

            logger.info("Wave %d started", wave.wave_number)
            self._tracker.add_event(
                "wave_started",
                f"Wave {wave.wave_number} started",
                {"wave_number": wave.wave_number},
            )

            wave.status = "running"
            batch_run.status = "running"
            self._tracker.save_state()

            await self.dispatch_wave(wave)
            await self.poll_wave(wave)

            wave.status = "completed"

            # Terminate completed Devin sessions to free concurrent slots
            await self._cleanup_sessions(wave)

            # Compute wave results
            success = wave.success_count
            total = wave.total_count
            prs = sum(1 for s in wave.sessions if s.pr_url is not None)

            logger.info(
                "Wave %d completed: %d/%d succeeded, %d PRs",
                wave.wave_number,
                success,
                total,
                prs,
            )
            self._tracker.add_event(
                "wave_completed",
                f"Wave {wave.wave_number} completed: {success}/{total} succeeded, {prs} PRs",
                {
                    "wave_number": wave.wave_number,
                    "success": success,
                    "total": total,
                    "prs": prs,
                },
            )
            self._tracker.save_state()

            # Check gate
            if not self.check_gate(wave):
                batch_run.status = "paused"
                self._tracker.add_event(
                    "wave_gated",
                    "Wave gated",
                    {
                        "wave_number": wave.wave_number,
                        "success_rate": success / total if total > 0 else 0.0,
                        "threshold": self._config.min_success_rate,
                    },
                )
                self._tracker.save_state()
                break

            # Retry failed sessions
            await self.retry_failed(wave)

        if batch_run.status != "paused":
            batch_run.status = "completed"

        self._tracker.add_event("run_completed", "Run completed")
        self._tracker.save_state()

        return batch_run

    async def dispatch_wave(self, wave: Wave) -> None:
        """Dispatch all sessions in a wave sequentially."""
        for i, session in enumerate(wave.sessions):
            # Determine per-session routing
            if self._config.hybrid_mode and self._mock_client:
                from orchestrator.devin.session_manager import determine_data_source
                ds = determine_data_source(session.finding, self._config)
                chosen_client = self._client if ds == "live" else self._mock_client
            else:
                ds = self._data_source
                chosen_client = self._client

            await create_remediation_session(
                chosen_client, session, self._config, ds,
                ledger=self._ledger, run_id=self._run_id,
            )
            self._tracker.add_event(
                "session_started",
                f"Session started for {session.finding.finding_id}",
                {
                    "finding_id": session.finding.finding_id,
                    "session_id": session.session_id,
                    "data_source": ds,
                },
            )
            self._tracker.update_session(session)

            # Brief pause between creates to let Devin register the session
            if i < len(wave.sessions) - 1:
                await asyncio.sleep(1)
        self._tracker.save_state()

    async def poll_wave(self, wave: Wave) -> None:
        """Poll all active sessions until they complete or timeout."""
        while True:
            active = [s for s in wave.sessions if s.status in _ACTIVE_STATUSES]
            if not active:
                break

            if self._config.hybrid_mode and self._mock_client:
                # Split by data_source and poll with the right client
                live_active = [s for s in active if s.data_source == "live"]
                mock_active = [s for s in active if s.data_source == "mock"]
                if live_active:
                    await poll_active_sessions(
                        self._client, live_active, self._tracker, self._config
                    )
                if mock_active:
                    await poll_active_sessions(
                        self._mock_client, mock_active, self._tracker, self._config
                    )
            else:
                await poll_active_sessions(
                    self._client, active, self._tracker, self._config
                )

            await asyncio.sleep(self._config.poll_interval_seconds)

    async def _cleanup_sessions(self, wave: Wave) -> None:
        """Terminate completed Devin sessions to free concurrent session slots."""
        for session in wave.sessions:
            if session.session_id is None:
                continue
            if session.status not in _TERMINAL_STATUSES:
                continue
            try:
                client = self._client
                if self._config.hybrid_mode and self._mock_client and session.data_source == "mock":
                    client = self._mock_client
                await client.terminate_session(session.session_id)
                logger.info(
                    "Terminated session %s (%s) to free concurrent slot",
                    session.session_id[:16],
                    session.finding.finding_id,
                )
            except Exception as exc:
                # Best-effort — don't block the run if termination fails
                logger.warning(
                    "Could not terminate session %s: %s",
                    session.session_id[:16],
                    exc,
                )

    async def _drain_stale_sessions(self) -> None:
        """Terminate any existing Devin sessions from previous runs to free slots."""
        try:
            response = await self._client.list_sessions(limit=20)
            # Real API returns a list, mock returns {"sessions": [...]}
            sessions_list = (
                response if isinstance(response, list)
                else response.get("sessions", [])
            )
            if not sessions_list:
                return

            logger.info(
                "Found %d existing Devin session(s) — terminating to free slots",
                len(sessions_list),
            )
            for s in sessions_list:
                sid = s.get("session_id", "")
                if not sid:
                    continue
                try:
                    # Use best-effort: 404 (already gone) won't trip circuit breaker
                    if hasattr(self._client, "terminate_session_best_effort"):
                        await self._client.terminate_session_best_effort(sid)
                    else:
                        await self._client.terminate_session(sid)
                    logger.info("Terminated stale session %s", sid[:16])
                except Exception:
                    pass  # Best-effort

            # Brief wait for Devin to release the slots
            await asyncio.sleep(3)
        except Exception as exc:
            logger.warning("Could not drain stale sessions: %s", exc)
        finally:
            # Reset circuit breaker after drain — cleanup failures should not
            # block the actual run from starting.
            if hasattr(self._client, "reset_circuit_breaker"):
                self._client.reset_circuit_breaker()
                logger.info("Circuit breaker reset after drain")

    def check_gate(self, wave: Wave) -> bool:
        """Return True if success rate meets threshold, False to pause."""
        total = wave.total_count
        if total == 0:
            return True

        completed = wave.success_count + wave.failure_count
        if completed == 0:
            return True

        success_rate = wave.success_count / total
        return success_rate >= self._config.min_success_rate

    async def retry_failed(self, wave: Wave) -> None:
        """Retry failed sessions in a wave (up to 2 total attempts)."""
        retryable: list[RemediationSession] = []

        for session in wave.sessions:
            if session.status in _RETRIABLE_STATUSES and session.attempt < 2:
                # Reset session for retry
                session.status = SessionStatus.PENDING
                session.session_id = None
                session.error_message = None
                session.completed_at = None
                session.pr_url = None
                session.structured_output = None
                session.attempt += 1

                self._tracker.add_event(
                    "session_retry",
                    f"Retrying {session.finding.finding_id} (attempt {session.attempt})",
                    {
                        "finding_id": session.finding.finding_id,
                        "attempt": session.attempt,
                    },
                )
                retryable.append(session)

        if not retryable:
            return

        # Dispatch retryable sessions sequentially
        for i, session in enumerate(retryable):
            if self._config.hybrid_mode and self._mock_client:
                from orchestrator.devin.session_manager import determine_data_source
                ds = determine_data_source(session.finding, self._config)
                chosen_client = self._client if ds == "live" else self._mock_client
            else:
                ds = self._data_source
                chosen_client = self._client

            await create_remediation_session(
                chosen_client, session, self._config, ds,
                ledger=self._ledger, run_id=self._run_id,
            )
            self._tracker.add_event(
                "session_started",
                f"Session started for {session.finding.finding_id}",
                {
                    "finding_id": session.finding.finding_id,
                    "session_id": session.session_id,
                    "data_source": ds,
                },
            )
            self._tracker.update_session(session)

            if i < len(retryable) - 1:
                await asyncio.sleep(1)
        self._tracker.save_state()

        # Poll only the retryable sessions until they complete
        while True:
            active = [s for s in retryable if s.status in _ACTIVE_STATUSES]
            if not active:
                break

            if self._config.hybrid_mode and self._mock_client:
                live_active = [s for s in active if s.data_source == "live"]
                mock_active = [s for s in active if s.data_source == "mock"]
                if live_active:
                    await poll_active_sessions(
                        self._client, live_active, self._tracker, self._config
                    )
                if mock_active:
                    await poll_active_sessions(
                        self._mock_client, mock_active, self._tracker, self._config
                    )
            else:
                await poll_active_sessions(
                    self._client, active, self._tracker, self._config
                )

            await asyncio.sleep(self._config.poll_interval_seconds)

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.models import BatchRun, RemediationSession, SessionStatus
from orchestrator.utils import atomic_write_json, with_file_lock

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {
    SessionStatus.SUCCESS,
    SessionStatus.FAILED,
    SessionStatus.TIMEOUT,
    SessionStatus.BLOCKED,
}

_FAILURE_STATUSES = {
    SessionStatus.FAILED,
    SessionStatus.TIMEOUT,
    SessionStatus.BLOCKED,
}

_ACTIVE_STATUSES = {
    SessionStatus.DISPATCHED,
    SessionStatus.WORKING,
}


class ProgressTracker:
    """Tracks aggregate progress of a BatchRun and persists state to disk.

    The state file (state.json) contains the full BatchRun serialized via
    model_dump(mode='json'). The Next.js dashboard reads this file via
    an API route every 5 seconds.
    """

    def __init__(
        self,
        batch_run: BatchRun,
        state_file_path: str = "./state.json",
        runs_dir: str = "./runs",
    ) -> None:
        self._batch_run = batch_run
        self._state_file_path = Path(state_file_path)
        self._runs_dir = Path(runs_dir)
        self._run_dir = self._runs_dir / batch_run.run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)

    @property
    def batch_run(self) -> BatchRun:
        return self._batch_run

    def update_session(self, session: RemediationSession) -> None:
        """Recount all aggregate counters by iterating all sessions across all waves."""
        completed = 0
        successful = 0
        failed = 0
        prs_created = 0

        for wave in self._batch_run.waves:
            wave_success = 0
            wave_failure = 0

            for sess in wave.sessions:
                if sess.status in _TERMINAL_STATUSES:
                    completed += 1
                if sess.status == SessionStatus.SUCCESS:
                    successful += 1
                    wave_success += 1
                if sess.status in _FAILURE_STATUSES:
                    failed += 1
                    wave_failure += 1
                if sess.pr_url is not None:
                    prs_created += 1

            wave.success_count = wave_success
            wave.failure_count = wave_failure

        self._batch_run.completed = completed
        self._batch_run.successful = successful
        self._batch_run.failed = failed
        self._batch_run.prs_created = prs_created

    def add_event(
        self,
        event_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add a timeline event to the batch run."""
        event: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "message": message,
            "details": details or {},
        }
        self._batch_run.events.append(event)

    def get_summary(self) -> dict[str, Any]:
        """Return aggregate stats for the dashboard overview cards."""
        active_sessions = 0
        pending_reviews = 0
        current_wave = 0

        for wave in self._batch_run.waves:
            has_non_pending = False
            for sess in wave.sessions:
                if sess.status in _ACTIVE_STATUSES:
                    active_sessions += 1
                if sess.pr_url is not None:
                    pending_reviews += 1
                if sess.status != SessionStatus.PENDING:
                    has_non_pending = True
            if has_non_pending and wave.wave_number > current_wave:
                current_wave = wave.wave_number

        completed = self._batch_run.completed
        success_rate = (
            self._batch_run.successful / completed if completed > 0 else 0.0
        )

        return {
            "total_findings": self._batch_run.total_findings,
            "completed": completed,
            "successful": self._batch_run.successful,
            "failed": self._batch_run.failed,
            "prs_created": self._batch_run.prs_created,
            "success_rate": success_rate,
            "active_sessions": active_sessions,
            "pending_reviews": pending_reviews,
            "status": self._batch_run.status,
            "current_wave": current_wave,
        }

    def extract_and_save_memories(self) -> int:
        """Extract memories from completed sessions and save to memory store.

        Returns the number of memory items saved.
        """
        from orchestrator.memory.extractor import extract_memories
        from orchestrator.memory.store import MemoryStore

        items = extract_memories(self._batch_run)
        if not items:
            return 0

        store = MemoryStore()
        graph = store.load_graph()

        for item in items:
            graph = store.upsert(item, graph)

        store.save_graph(graph)
        logger.info(
            "Saved %d memory items from run %s", len(items), self._batch_run.run_id
        )
        return len(items)

    def save_state(self) -> None:
        """Write state to runs/<run_id>/state.json, update index, and legacy path."""
        data = self._batch_run.model_dump(mode="json")

        # Per-run state
        run_state_path = self._run_dir / "state.json"
        atomic_write_json(run_state_path, data)

        # Update runs/index.json (with lock for cross-process safety)
        self._update_index()

        # Legacy backward compatibility
        atomic_write_json(self._state_file_path, data)

        logger.debug("Saved state to %s and %s", run_state_path, self._state_file_path)

    def _update_index(self) -> None:
        """Update or insert this run's entry in runs/index.json."""
        index_path = self._runs_dir / "index.json"

        with with_file_lock(index_path):
            # Load existing index
            entries: list[dict[str, Any]] = []
            if index_path.exists():
                try:
                    entries = json.loads(index_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    entries = []

            # Build summary for this run
            summary = {
                "run_id": self._batch_run.run_id,
                "started_at": (
                    self._batch_run.started_at.isoformat()
                    if hasattr(self._batch_run.started_at, "isoformat")
                    else str(self._batch_run.started_at)
                ),
                "status": self._batch_run.status,
                "total_findings": self._batch_run.total_findings,
                "csv_filename": None,
                "data_source": self._batch_run.data_source,
            }

            # Upsert: replace existing entry or append
            found = False
            for i, entry in enumerate(entries):
                if entry.get("run_id") == self._batch_run.run_id:
                    entries[i] = summary
                    found = True
                    break
            if not found:
                entries.append(summary)

            atomic_write_json(index_path, entries)

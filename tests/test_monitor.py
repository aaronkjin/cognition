import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from orchestrator.config import OrchestratorConfig
from orchestrator.models import (
    BatchRun, Finding, FindingCategory, RemediationSession,
    SessionStatus, Severity, Wave,
)
from orchestrator.monitor.tracker import ProgressTracker
from orchestrator.monitor.poller import poll_session, poll_active_sessions


def _make_finding(fid: str = "FIND-0001") -> Finding:
    return Finding(
        finding_id=fid, scanner="test", category=FindingCategory.SQL_INJECTION,
        severity=Severity.HIGH, title="Test", description="Test",
        service_name="test-svc", repo_url="https://github.com/test/repo",
        file_path="test.py", priority_score=70.0,
    )


def _make_session(fid: str = "FIND-0001", status: SessionStatus = SessionStatus.PENDING, wave: int = 1) -> RemediationSession:
    return RemediationSession(
        finding=_make_finding(fid), playbook_id="pb-test",
        status=status, wave_number=wave, attempt=1,
    )


def _make_batch_run(sessions_per_wave: list[int] = [2, 2]) -> BatchRun:
    waves = []
    fid_counter = 1
    for wave_num, count in enumerate(sessions_per_wave, start=1):
        sessions = []
        for _ in range(count):
            sessions.append(_make_session(f"FIND-{fid_counter:04d}", wave=wave_num))
            fid_counter += 1
        waves.append(Wave(wave_number=wave_num, sessions=sessions))
    return BatchRun(
        run_id="test-run-001",
        started_at=datetime.now(timezone.utc),
        waves=waves,
        total_findings=sum(sessions_per_wave),
    )


class TestProgressTracker:
    def test_initial_summary(self):
        run = _make_batch_run()
        tracker = ProgressTracker(run)
        summary = tracker.get_summary()
        assert summary["total_findings"] == 4
        assert summary["completed"] == 0
        assert summary["success_rate"] == 0.0

    def test_update_session_counts(self):
        run = _make_batch_run([3])
        tracker = ProgressTracker(run)

        # Simulate 2 successes, 1 failure
        run.waves[0].sessions[0].status = SessionStatus.SUCCESS
        run.waves[0].sessions[0].pr_url = "https://github.com/org/repo/pull/1"
        tracker.update_session(run.waves[0].sessions[0])

        run.waves[0].sessions[1].status = SessionStatus.SUCCESS
        run.waves[0].sessions[1].pr_url = "https://github.com/org/repo/pull/2"
        tracker.update_session(run.waves[0].sessions[1])

        run.waves[0].sessions[2].status = SessionStatus.FAILED
        tracker.update_session(run.waves[0].sessions[2])

        summary = tracker.get_summary()
        assert summary["completed"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["prs_created"] == 2
        assert summary["success_rate"] == pytest.approx(2 / 3)

    def test_add_event(self):
        run = _make_batch_run()
        tracker = ProgressTracker(run)
        tracker.add_event("session_started", "Session FIND-0001 started", {"finding_id": "FIND-0001"})

        assert len(run.events) == 1
        assert run.events[0]["event_type"] == "session_started"
        assert run.events[0]["message"] == "Session FIND-0001 started"
        assert "timestamp" in run.events[0]

    def test_save_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = str(Path(tmpdir) / "state.json")
            run = _make_batch_run()
            tracker = ProgressTracker(run, state_file_path=state_path)
            tracker.save_state()

            # Verify file exists and is valid JSON
            data = json.loads(Path(state_path).read_text())
            assert data["run_id"] == "test-run-001"
            assert len(data["waves"]) == 2

            # Verify it can be deserialized back
            restored = BatchRun.model_validate(data)
            assert restored.run_id == "test-run-001"


class TestPoller:
    @pytest.mark.asyncio
    async def test_poll_session_working(self):
        mock_client = AsyncMock()
        mock_client.get_session.return_value = {
            "status_enum": "working",
            "structured_output": {"status": "fixing", "progress_pct": 45},
            "pull_request": None,
        }

        session = _make_session(status=SessionStatus.DISPATCHED)
        session.session_id = "ses-123"

        result = await poll_session(mock_client, session)
        assert result.status == SessionStatus.WORKING
        assert result.structured_output is not None

    @pytest.mark.asyncio
    async def test_poll_session_finished(self):
        mock_client = AsyncMock()
        mock_client.get_session.return_value = {
            "status_enum": "finished",
            "structured_output": {"status": "completed", "progress_pct": 100},
            "pull_request": {"url": "https://github.com/org/repo/pull/42"},
        }

        session = _make_session(status=SessionStatus.WORKING)
        session.session_id = "ses-123"

        result = await poll_session(mock_client, session)
        assert result.status == SessionStatus.SUCCESS
        assert result.pr_url == "https://github.com/org/repo/pull/42"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_poll_session_api_error(self):
        mock_client = AsyncMock()
        mock_client.get_session.side_effect = Exception("Connection refused")

        session = _make_session(status=SessionStatus.WORKING)
        session.session_id = "ses-123"

        result = await poll_session(mock_client, session)
        # Should return session unchanged, not crash
        assert result.status == SessionStatus.WORKING

    @pytest.mark.asyncio
    async def test_poll_active_sessions_filters_inactive(self):
        mock_client = AsyncMock()
        mock_client.get_session.return_value = {
            "status_enum": "working",
            "structured_output": {"status": "fixing"},
            "pull_request": None,
        }

        sessions = [
            _make_session("F-1", status=SessionStatus.PENDING),       # skip
            _make_session("F-2", status=SessionStatus.DISPATCHED),    # poll
            _make_session("F-3", status=SessionStatus.WORKING),       # poll
            _make_session("F-4", status=SessionStatus.SUCCESS),       # skip
        ]
        sessions[1].session_id = "ses-2"
        sessions[2].session_id = "ses-3"

        tracker = ProgressTracker(
            _make_batch_run([4]),
            state_file_path="/tmp/test_state.json",
        )

        still_active = await poll_active_sessions(mock_client, sessions, tracker, OrchestratorConfig())

        # Only sessions 1 and 2 (DISPATCHED and WORKING) should have been polled
        assert mock_client.get_session.call_count == 2
        # Both are still active (working)
        assert len(still_active) == 2

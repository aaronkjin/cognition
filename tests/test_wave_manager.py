import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.config import OrchestratorConfig
from orchestrator.models import (
    BatchRun, Finding, FindingCategory, RemediationSession,
    SessionStatus, Severity, Wave,
)
from orchestrator.monitor.tracker import ProgressTracker
from orchestrator.planner.wave_manager import WaveManager


def _make_finding(fid: str = "FIND-0001") -> Finding:
    return Finding(
        finding_id=fid, scanner="test", category=FindingCategory.SQL_INJECTION,
        severity=Severity.HIGH, title="Test", description="Test",
        service_name="test-svc", repo_url="https://github.com/test/repo",
        file_path="test.py", priority_score=70.0,
    )


def _make_session(fid: str = "FIND-0001", wave: int = 1) -> RemediationSession:
    return RemediationSession(
        finding=_make_finding(fid), playbook_id="pb-test",
        status=SessionStatus.PENDING, wave_number=wave, attempt=1,
    )


def _make_batch_run(sessions_per_wave: list[int]) -> BatchRun:
    waves = []
    fid_counter = 1
    for wave_num, count in enumerate(sessions_per_wave, start=1):
        sessions = [_make_session(f"FIND-{fid_counter + i:04d}", wave=wave_num) for i in range(count)]
        fid_counter += count
        waves.append(Wave(wave_number=wave_num, sessions=sessions))
    return BatchRun(
        run_id="test-run", started_at=datetime.now(timezone.utc),
        waves=waves, total_findings=sum(sessions_per_wave),
    )


class TestCheckGate:
    def test_passes_when_above_threshold(self):
        config = OrchestratorConfig(min_success_rate=0.7)
        run = _make_batch_run([5])
        tracker = ProgressTracker(run, state_file_path="/tmp/test.json")
        wm = WaveManager(AsyncMock(), config, tracker)

        # 4/5 success = 80% > 70%
        wave = run.waves[0]
        wave.success_count = 4
        wave.failure_count = 1
        assert wm.check_gate(wave) is True

    def test_fails_when_below_threshold(self):
        config = OrchestratorConfig(min_success_rate=0.7)
        run = _make_batch_run([5])
        tracker = ProgressTracker(run, state_file_path="/tmp/test.json")
        wm = WaveManager(AsyncMock(), config, tracker)

        # 2/5 success = 40% < 70%
        wave = run.waves[0]
        wave.success_count = 2
        wave.failure_count = 3
        assert wm.check_gate(wave) is False

    def test_passes_on_empty_wave(self):
        config = OrchestratorConfig(min_success_rate=0.7)
        run = _make_batch_run([3])
        tracker = ProgressTracker(run, state_file_path="/tmp/test.json")
        wm = WaveManager(AsyncMock(), config, tracker)

        wave = run.waves[0]
        # No completions yet
        assert wm.check_gate(wave) is True


class TestDispatchWave:
    @pytest.mark.asyncio
    async def test_dispatches_all_sessions(self):
        config = OrchestratorConfig(max_parallel_sessions=10)
        run = _make_batch_run([3])
        tracker = ProgressTracker(run, state_file_path="/tmp/test.json")

        mock_client = AsyncMock()
        mock_client.create_session.return_value = {
            "session_id": "ses-test",
            "url": "https://app.devin.ai/sessions/ses-test",
            "is_new_session": True,
        }

        wm = WaveManager(mock_client, config, tracker)
        await wm.dispatch_wave(run.waves[0])

        # All 3 sessions should have been dispatched
        assert mock_client.create_session.call_count == 3
        for session in run.waves[0].sessions:
            assert session.status in (SessionStatus.DISPATCHED, SessionStatus.FAILED)


class TestRetryFailed:
    @pytest.mark.asyncio
    async def test_retries_failed_sessions(self):
        config = OrchestratorConfig(max_parallel_sessions=10, poll_interval_seconds=0)
        run = _make_batch_run([3])
        tracker = ProgressTracker(run, state_file_path="/tmp/test.json")

        # Simulate: session 0 succeeded, session 1 failed, session 2 timed out
        wave = run.waves[0]
        wave.sessions[0].status = SessionStatus.SUCCESS
        wave.sessions[0].attempt = 1
        wave.sessions[1].status = SessionStatus.FAILED
        wave.sessions[1].attempt = 1
        wave.sessions[2].status = SessionStatus.TIMEOUT
        wave.sessions[2].attempt = 1

        mock_client = AsyncMock()
        mock_client.create_session.return_value = {
            "session_id": "ses-retry",
            "url": "https://app.devin.ai/sessions/ses-retry",
            "is_new_session": True,
        }
        # Make get_session return finished immediately so poll_wave exits
        mock_client.get_session.return_value = {
            "status_enum": "finished",
            "structured_output": {"status": "completed", "progress_pct": 100},
            "pull_request": {"url": "https://github.com/test/repo/pull/1"},
        }

        wm = WaveManager(mock_client, config, tracker)
        await wm.retry_failed(wave)

        # Sessions 1 and 2 should have been retried (attempt=2)
        assert wave.sessions[1].attempt == 2
        assert wave.sessions[2].attempt == 2
        # Session 0 was not retried
        assert wave.sessions[0].attempt == 1

    @pytest.mark.asyncio
    async def test_does_not_retry_max_attempts(self):
        config = OrchestratorConfig(max_parallel_sessions=10, poll_interval_seconds=0)
        run = _make_batch_run([1])
        tracker = ProgressTracker(run, state_file_path="/tmp/test.json")

        wave = run.waves[0]
        wave.sessions[0].status = SessionStatus.FAILED
        wave.sessions[0].attempt = 2  # Already at max

        mock_client = AsyncMock()
        wm = WaveManager(mock_client, config, tracker)
        await wm.retry_failed(wave)

        # Should NOT have been retried
        assert wave.sessions[0].attempt == 2
        assert mock_client.create_session.call_count == 0

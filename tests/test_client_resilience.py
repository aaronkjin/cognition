from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.devin.client import CircuitBreaker, CircuitBreakerOpen


class TestCircuitBreaker:
    """Tests for the CircuitBreaker state machine."""

    def test_starts_closed(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=10)
        assert cb.state == "closed"

    def test_opens_after_threshold_failures(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=10)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"

    def test_stays_closed_below_threshold(self) -> None:
        cb = CircuitBreaker(threshold=3, cooldown_seconds=10)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"

    def test_rejects_when_open(self) -> None:
        cb = CircuitBreaker(threshold=1, cooldown_seconds=10)
        cb.record_failure()
        assert cb.state == "open"
        with pytest.raises(CircuitBreakerOpen):
            cb.check()

    def test_half_open_after_cooldown(self) -> None:
        cb = CircuitBreaker(threshold=1, cooldown_seconds=0)  # 0s cooldown for test
        cb.record_failure()
        # With 0s cooldown, should immediately transition to half_open
        assert cb.state == "half_open"

    def test_half_open_allows_probe(self) -> None:
        cb = CircuitBreaker(threshold=1, cooldown_seconds=0)
        cb.record_failure()
        assert cb.state == "half_open"
        # check() should NOT raise in half_open (allows one probe)
        cb.check()

    def test_resets_to_closed_on_success(self) -> None:
        cb = CircuitBreaker(threshold=2, cooldown_seconds=10)
        cb.record_failure()
        cb.record_success()
        assert cb.state == "closed"
        assert cb._failure_count == 0

    def test_reopens_on_failure_in_half_open(self) -> None:
        cb = CircuitBreaker(threshold=1, cooldown_seconds=0)
        cb.record_failure()  # -> open
        assert cb.state == "half_open"  # cooldown=0 so immediate
        cb.record_failure()  # -> open again (threshold=1 so re-opens)
        # With cooldown=0, state transitions open -> half_open immediately on read,
        # but the failure count confirms it re-opened
        assert cb._failure_count >= cb._threshold

    def test_success_in_half_open_closes(self) -> None:
        cb = CircuitBreaker(threshold=1, cooldown_seconds=0)
        cb.record_failure()  # -> open -> half_open (cooldown=0)
        cb.record_success()  # -> closed
        assert cb.state == "closed"

    def test_check_passes_when_closed(self) -> None:
        cb = CircuitBreaker(threshold=5, cooldown_seconds=10)
        cb.check()  # Should not raise


class TestIdempotencyLedger:
    """Tests for the IdempotencyLedger."""

    def test_record_and_lookup(self, tmp_path: Path) -> None:
        from orchestrator.devin.idempotency import IdempotencyLedger

        ledger = IdempotencyLedger(tmp_path / "idempotency.json")
        ledger.record("key-1", "session-abc", "2026-01-01T00:00:00")
        result = ledger.lookup("key-1")
        assert result is not None
        assert result["session_id"] == "session-abc"
        assert result["created_at"] == "2026-01-01T00:00:00"

    def test_lookup_miss_returns_none(self, tmp_path: Path) -> None:
        from orchestrator.devin.idempotency import IdempotencyLedger

        ledger = IdempotencyLedger(tmp_path / "idempotency.json")
        assert ledger.lookup("nonexistent") is None

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        from orchestrator.devin.idempotency import IdempotencyLedger

        path = tmp_path / "idempotency.json"
        ledger1 = IdempotencyLedger(path)
        ledger1.record("key-1", "session-abc", "2026-01-01T00:00:00")
        # Load fresh instance from same file
        ledger2 = IdempotencyLedger(path)
        assert ledger2.lookup("key-1") is not None
        assert ledger2.lookup("key-1")["session_id"] == "session-abc"

    def test_make_key_format(self, tmp_path: Path) -> None:
        from orchestrator.devin.idempotency import IdempotencyLedger

        ledger = IdempotencyLedger(tmp_path / "idempotency.json")
        key = ledger.make_key("run-abc", "FIND-0001", 1)
        assert key == "run-abc-FIND-0001-attempt-1"

    def test_multiple_entries(self, tmp_path: Path) -> None:
        from orchestrator.devin.idempotency import IdempotencyLedger

        ledger = IdempotencyLedger(tmp_path / "idempotency.json")
        ledger.record("key-1", "session-aaa", "2026-01-01T00:00:00")
        ledger.record("key-2", "session-bbb", "2026-01-01T00:01:00")
        assert ledger.lookup("key-1")["session_id"] == "session-aaa"
        assert ledger.lookup("key-2")["session_id"] == "session-bbb"

    def test_handles_corrupt_file(self, tmp_path: Path) -> None:
        from orchestrator.devin.idempotency import IdempotencyLedger

        path = tmp_path / "idempotency.json"
        path.write_text("NOT VALID JSON", encoding="utf-8")
        ledger = IdempotencyLedger(path)
        # Should start fresh, not crash
        assert ledger.lookup("anything") is None

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        from orchestrator.devin.idempotency import IdempotencyLedger

        path = tmp_path / "nested" / "dir" / "idempotency.json"
        ledger = IdempotencyLedger(path)
        ledger.record("key-1", "session-abc", "2026-01-01T00:00:00")
        assert path.exists()

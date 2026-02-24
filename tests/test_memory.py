from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orchestrator.memory.extractor import extract_memories
from orchestrator.memory.models import MemoryGraph, MemoryGraphEntry, MemoryItem
from orchestrator.memory.retriever import retrieve_memories
from orchestrator.memory.store import MemoryStore
from orchestrator.models import (
    BatchRun,
    Finding,
    FindingCategory,
    RemediationSession,
    SessionStatus,
    Severity,
    Wave,
)


def _make_finding(
    finding_id: str = "FIND-0001",
    category: str = "sql_injection",
    service: str = "payment-service",
    severity: str = "high",
) -> Finding:
    return Finding(
        finding_id=finding_id,
        scanner="test",
        category=FindingCategory(category),
        severity=Severity(severity),
        title=f"Test finding {finding_id}",
        description="Test description",
        service_name=service,
        repo_url="https://github.com/test/repo",
        file_path="src/test.py",
    )


def _make_session(
    finding: Finding,
    status: SessionStatus = SessionStatus.SUCCESS,
    pr_url: str | None = "https://github.com/test/repo/pull/1",
    data_source: str = "mock",
) -> RemediationSession:
    return RemediationSession(
        session_id="mock-abc123",
        finding=finding,
        playbook_id="pb-test",
        status=status,
        data_source=data_source,
        pr_url=pr_url,
        structured_output={
            "finding_id": finding.finding_id,
            "status": "completed",
            "progress_pct": 100,
            "current_step": "Done",
            "fix_approach": "Parameterized the SQL query",
            "files_modified": ["src/dao.py", "tests/test_dao.py"],
            "tests_passed": True,
            "tests_added": 2,
            "confidence": "high",
        },
    )


def _make_batch_run(sessions: list[RemediationSession]) -> BatchRun:
    return BatchRun(
        run_id="test-run",
        started_at=datetime.now(timezone.utc),
        waves=[Wave(wave_number=1, sessions=sessions)],
        total_findings=len(sessions),
    )


class TestExtractor:
    def test_extracts_from_success(self) -> None:
        finding = _make_finding()
        session = _make_session(finding, SessionStatus.SUCCESS)
        run = _make_batch_run([session])
        items = extract_memories(run)
        assert len(items) == 1
        assert items[0].outcome == "success"
        assert items[0].fix_approach == "Parameterized the SQL query"

    def test_item_id_includes_run_id(self) -> None:
        finding = _make_finding("FIND-0042")
        session = _make_session(finding, SessionStatus.SUCCESS)
        run = _make_batch_run([session])
        items = extract_memories(run)
        assert items[0].item_id == "test-run-FIND-0042"
        assert items[0].finding_id == "FIND-0042"

    def test_extracts_from_failed(self) -> None:
        finding = _make_finding()
        session = _make_session(finding, SessionStatus.FAILED, pr_url=None)
        session.error_message = "Tests broke"
        run = _make_batch_run([session])
        items = extract_memories(run)
        assert len(items) == 1
        assert items[0].outcome == "failed"

    def test_skips_pending(self) -> None:
        finding = _make_finding()
        session = _make_session(finding, SessionStatus.PENDING)
        run = _make_batch_run([session])
        items = extract_memories(run)
        assert len(items) == 0

    def test_skips_working(self) -> None:
        finding = _make_finding()
        session = _make_session(finding, SessionStatus.WORKING)
        run = _make_batch_run([session])
        items = extract_memories(run)
        assert len(items) == 0


class TestStore:
    def test_save_and_load_graph(self, tmp_path: Path) -> None:
        store = MemoryStore(tmp_path / "memory")
        graph = MemoryGraph()
        entry = MemoryGraphEntry(
            item_id="FIND-0001",
            finding_id="FIND-0001",
            category="sql_injection",
            service_name="payment-service",
            severity="high",
            data_source="mock",
            outcome="success",
            created_at=datetime.now(timezone.utc).isoformat(),
            run_id="test-run",
        )
        graph.entries.append(entry)
        store.save_graph(graph)
        loaded = store.load_graph()
        assert len(loaded.entries) == 1
        assert loaded.entries[0].item_id == "FIND-0001"

    def test_save_and_load_item(self, tmp_path: Path) -> None:
        store = MemoryStore(tmp_path / "memory")
        item = MemoryItem(
            item_id="FIND-0001",
            finding_id="FIND-0001",
            category="sql_injection",
            service_name="payment-service",
            severity="high",
            title="Test SQL Injection",
            data_source="mock",
            outcome="success",
            fix_approach="Used parameterized queries",
            run_id="test-run",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        store.save_item(item)
        content = store.load_item("FIND-0001")
        assert content is not None
        assert "sql_injection" in content
        assert "Used parameterized queries" in content

    def test_upsert_updates_existing(self, tmp_path: Path) -> None:
        store = MemoryStore(tmp_path / "memory")
        graph = MemoryGraph()
        item1 = MemoryItem(
            item_id="FIND-0001",
            finding_id="FIND-0001",
            category="sql_injection",
            service_name="svc",
            severity="high",
            title="T",
            data_source="mock",
            outcome="failed",
            run_id="run-1",
            created_at="2026-01-01T00:00:00",
        )
        graph = store.upsert(item1, graph)
        assert len(graph.entries) == 1
        assert graph.entries[0].outcome == "failed"

        item2 = MemoryItem(
            item_id="FIND-0001",
            finding_id="FIND-0001",
            category="sql_injection",
            service_name="svc",
            severity="high",
            title="T",
            data_source="live",
            outcome="success",
            run_id="run-2",
            created_at="2026-01-02T00:00:00",
        )
        graph = store.upsert(item2, graph)
        assert len(graph.entries) == 1
        assert graph.entries[0].outcome == "success"


class TestRetriever:
    def _build_store_with_entries(self, tmp_path: Path) -> MemoryStore:
        store = MemoryStore(tmp_path / "memory")
        graph = MemoryGraph()

        # SQL injection in payment-service (success, high confidence)
        item1 = MemoryItem(
            item_id="run-1-FIND-0001",
            finding_id="FIND-0001",
            category="sql_injection",
            service_name="payment-service",
            severity="high",
            title="SQL Fix",
            data_source="live",
            outcome="success",
            confidence="high",
            fix_approach="Parameterized queries",
            run_id="run-1",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        graph = store.upsert(item1, graph)

        # SQL injection in user-service (failed)
        item2 = MemoryItem(
            item_id="run-1-FIND-0002",
            finding_id="FIND-0002",
            category="sql_injection",
            service_name="user-service",
            severity="high",
            title="SQL Fix 2",
            data_source="mock",
            outcome="failed",
            error_message="Tests failed",
            run_id="run-1",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        graph = store.upsert(item2, graph)

        # Dependency vuln in payment-service (success)
        item3 = MemoryItem(
            item_id="run-1-FIND-0003",
            finding_id="FIND-0003",
            category="dependency_vulnerability",
            service_name="payment-service",
            severity="critical",
            title="Dep Fix",
            data_source="mock",
            outcome="success",
            confidence="medium",
            fix_approach="Upgraded dependency",
            run_id="run-1",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        graph = store.upsert(item3, graph)

        store.save_graph(graph)
        return store

    def test_retrieves_same_category_first(self, tmp_path: Path) -> None:
        store = self._build_store_with_entries(tmp_path)
        finding = _make_finding("FIND-NEW", "sql_injection", "catalog-service")
        results = retrieve_memories(finding, store, max_results=3)
        # Should return SQL injection memories first
        assert len(results) >= 1
        assert "sql_injection" in results[0]["content"].lower() or "SQL" in results[0]["content"]

    def test_prefers_live_over_mock(self, tmp_path: Path) -> None:
        store = self._build_store_with_entries(tmp_path)
        finding = _make_finding("FIND-NEW", "sql_injection", "payment-service")
        results = retrieve_memories(finding, store, max_results=3)
        # First result should be the live one (FIND-0001)
        assert results[0]["data_source"] == "live"

    def test_mock_note_included(self, tmp_path: Path) -> None:
        store = self._build_store_with_entries(tmp_path)
        finding = _make_finding("FIND-NEW", "sql_injection", "user-service")
        results = retrieve_memories(finding, store, max_results=3)
        mock_results = [r for r in results if r["data_source"] == "mock"]
        if mock_results:
            assert "mock session" in mock_results[0]["source_note"].lower()

    def test_returns_empty_for_no_match(self, tmp_path: Path) -> None:
        store = self._build_store_with_entries(tmp_path)
        finding = _make_finding("FIND-NEW", "xss", "other-service")
        results = retrieve_memories(finding, store, max_results=3)
        assert len(results) == 0

    def test_max_results_respected(self, tmp_path: Path) -> None:
        store = self._build_store_with_entries(tmp_path)
        finding = _make_finding("FIND-NEW", "sql_injection", "payment-service")
        results = retrieve_memories(finding, store, max_results=1)
        assert len(results) <= 1

    def test_cross_run_accumulation(self, tmp_path: Path) -> None:
        """Same finding across two runs should produce two distinct graph entries."""
        store = MemoryStore(tmp_path / "memory")
        graph = MemoryGraph()

        item_run1 = MemoryItem(
            item_id="run-1-FIND-0001",
            finding_id="FIND-0001",
            category="sql_injection",
            service_name="payment-service",
            severity="high",
            title="SQL Fix",
            data_source="mock",
            outcome="failed",
            run_id="run-1",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        graph = store.upsert(item_run1, graph)

        item_run2 = MemoryItem(
            item_id="run-2-FIND-0001",
            finding_id="FIND-0001",
            category="sql_injection",
            service_name="payment-service",
            severity="high",
            title="SQL Fix",
            data_source="live",
            outcome="success",
            confidence="high",
            fix_approach="Used parameterized queries",
            run_id="run-2",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        graph = store.upsert(item_run2, graph)

        # Both entries should exist (not overwritten)
        assert len(graph.entries) == 2
        assert graph.entries[0].item_id == "run-1-FIND-0001"
        assert graph.entries[1].item_id == "run-2-FIND-0001"

        # They should have a same_category + same_service relationship
        assert len(graph.entries[1].relationships) >= 1
        rel_targets = {r.target_id for r in graph.entries[1].relationships}
        assert "run-1-FIND-0001" in rel_targets

        # Retrieval should return both, with live/success ranked higher
        store.save_graph(graph)
        finding = _make_finding("FIND-NEW", "sql_injection", "payment-service")
        results = retrieve_memories(finding, store, max_results=3)
        assert len(results) == 2
        assert results[0]["data_source"] == "live"  # live + success ranked first

import pytest

from orchestrator.models import (
    Finding, FindingCategory, RemediationSession, Severity, SessionStatus, Wave,
)
from orchestrator.planner.batch_planner import create_waves
from orchestrator.planner.playbook_selector import (
    PLAYBOOK_MAP, FALLBACK_PLAYBOOK, get_playbook_path, assign_playbooks,
)


def _make_finding(fid: str, category: FindingCategory, severity: Severity, score: float) -> Finding:
    """Helper to create a minimal Finding for testing."""
    return Finding(
        finding_id=fid,
        scanner="test",
        category=category,
        severity=severity,
        title=f"Test finding {fid}",
        description="Test",
        service_name="test-service",
        repo_url="https://github.com/test/repo",
        file_path="test.py",
        priority_score=score,
    )


class TestCreateWaves:
    def test_basic_chunking(self):
        """20 findings with wave_size=5 → 4 waves."""
        findings = [
            _make_finding(f"F-{i:03d}", FindingCategory.SQL_INJECTION, Severity.HIGH, 100 - i)
            for i in range(20)
        ]
        waves = create_waves(findings, wave_size=5)
        assert len(waves) == 4
        for i, wave in enumerate(waves):
            assert wave.wave_number == i + 1
            assert len(wave.sessions) == 5
            assert wave.status == "pending"

    def test_wave_numbering(self):
        """Wave numbers start at 1."""
        findings = [_make_finding("F-001", FindingCategory.XSS, Severity.LOW, 10)]
        waves = create_waves(findings, wave_size=10)
        assert len(waves) == 1
        assert waves[0].wave_number == 1

    def test_session_fields(self):
        """Each session has correct initial state."""
        f = _make_finding("F-001", FindingCategory.SQL_INJECTION, Severity.CRITICAL, 85)
        waves = create_waves([f], wave_size=10)
        session = waves[0].sessions[0]
        assert session.finding.finding_id == "F-001"
        assert session.playbook_id == ""
        assert session.status == SessionStatus.PENDING
        assert session.wave_number == 1
        assert session.attempt == 1

    def test_partial_last_wave(self):
        """7 findings with wave_size=3 → 3 waves (3, 3, 1)."""
        findings = [
            _make_finding(f"F-{i}", FindingCategory.PII_LOGGING, Severity.MEDIUM, 50 - i)
            for i in range(7)
        ]
        waves = create_waves(findings, wave_size=3)
        assert len(waves) == 3
        assert len(waves[0].sessions) == 3
        assert len(waves[1].sessions) == 3
        assert len(waves[2].sessions) == 1

    def test_priority_order_preserved(self):
        """Wave 1 should contain the highest-priority findings."""
        findings = [
            _make_finding("HIGH", FindingCategory.SQL_INJECTION, Severity.CRITICAL, 85),
            _make_finding("MED", FindingCategory.PII_LOGGING, Severity.MEDIUM, 45),
            _make_finding("LOW", FindingCategory.ACCESS_LOGGING, Severity.LOW, 25),
        ]
        waves = create_waves(findings, wave_size=2)
        assert waves[0].sessions[0].finding.finding_id == "HIGH"
        assert waves[0].sessions[1].finding.finding_id == "MED"
        assert waves[1].sessions[0].finding.finding_id == "LOW"

    def test_empty_findings(self):
        """Empty input returns empty list."""
        waves = create_waves([], wave_size=5)
        assert waves == []


class TestPlaybookSelector:
    def test_known_categories(self):
        """Each mapped category returns its specific playbook."""
        assert get_playbook_path(FindingCategory.SQL_INJECTION) == "playbooks/sql_injection.devin.md"
        assert get_playbook_path(FindingCategory.HARDCODED_SECRET) == "playbooks/hardcoded_secrets.devin.md"
        assert get_playbook_path(FindingCategory.DEPENDENCY_VULNERABILITY) == \
            "playbooks/dependency_vulnerability.devin.md"
        assert get_playbook_path(FindingCategory.PII_LOGGING) == "playbooks/pii_logging.devin.md"
        assert get_playbook_path(FindingCategory.MISSING_ENCRYPTION) == \
            "playbooks/missing_encryption.devin.md"
        assert get_playbook_path(FindingCategory.ACCESS_LOGGING) == "playbooks/access_logging.devin.md"

    def test_fallback_categories(self):
        """XSS, PATH_TRAVERSAL, OTHER use fallback."""
        assert get_playbook_path(FindingCategory.XSS) == FALLBACK_PLAYBOOK
        assert get_playbook_path(FindingCategory.PATH_TRAVERSAL) == FALLBACK_PLAYBOOK
        assert get_playbook_path(FindingCategory.OTHER) == FALLBACK_PLAYBOOK

    def test_assign_playbooks(self):
        """assign_playbooks sets playbook_id on every session."""
        findings = [
            _make_finding("F-001", FindingCategory.SQL_INJECTION, Severity.HIGH, 70),
            _make_finding("F-002", FindingCategory.PII_LOGGING, Severity.MEDIUM, 45),
        ]
        waves = create_waves(findings, wave_size=10)

        playbook_ids = {
            "playbooks/sql_injection.devin.md": "pb-001",
            "playbooks/pii_logging.devin.md": "pb-002",
        }
        assign_playbooks(waves, playbook_ids)

        assert waves[0].sessions[0].playbook_id == "pb-001"
        assert waves[0].sessions[1].playbook_id == "pb-002"

    def test_assign_playbooks_with_fallback(self):
        """Categories without a specific playbook_id use first available."""
        findings = [
            _make_finding("F-001", FindingCategory.XSS, Severity.HIGH, 60),
        ]
        waves = create_waves(findings, wave_size=10)

        playbook_ids = {
            "playbooks/dependency_vulnerability.devin.md": "pb-fallback",
        }
        assign_playbooks(waves, playbook_ids)

        assert waves[0].sessions[0].playbook_id == "pb-fallback"

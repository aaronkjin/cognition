import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orchestrator.models import (
    BatchRun,
    Finding,
    FindingCategory,
    RemediationSession,
    SessionStatus,
    Severity,
    Wave,
)
from orchestrator.devin.session_manager import (
    build_remediation_prompt,
    load_service_overrides,
)


def _make_finding(**kwargs: object) -> Finding:
    defaults = dict(
        finding_id="FIND-0001",
        scanner="test",
        category=FindingCategory.SQL_INJECTION,
        severity=Severity.HIGH,
        title="Test",
        description="Test",
        service_name="svc",
        repo_url="https://github.com/test/repo",
        file_path="test.py",
    )
    defaults.update(kwargs)
    return Finding(**defaults)  # type: ignore[arg-type]


class TestReviewFields:
    """Test that review fields exist and serialize correctly."""

    def test_review_fields_default_none(self) -> None:
        finding = _make_finding()
        session = RemediationSession(finding=finding, playbook_id="pb-test")
        assert session.review_status is None
        assert session.reviewed_by is None
        assert session.reviewed_at is None
        assert session.review_reason is None

    def test_review_fields_serialize(self) -> None:
        finding = _make_finding()
        session = RemediationSession(
            finding=finding,
            playbook_id="pb-test",
            review_status="approved",
            reviewed_by="alice",
            reviewed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            review_reason="LGTM",
        )
        data = session.model_dump(mode="json")
        assert data["review_status"] == "approved"
        assert data["reviewed_by"] == "alice"
        assert data["review_reason"] == "LGTM"
        assert data["reviewed_at"] is not None

    def test_review_fields_rejected(self) -> None:
        finding = _make_finding()
        session = RemediationSession(
            finding=finding,
            playbook_id="pb-test",
            review_status="rejected",
            reviewed_by="bob",
            reviewed_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
            review_reason="Needs more tests",
        )
        data = session.model_dump(mode="json")
        assert data["review_status"] == "rejected"
        assert data["reviewed_by"] == "bob"
        assert data["review_reason"] == "Needs more tests"

    def test_version_increment(self) -> None:
        finding = _make_finding()
        session = RemediationSession(finding=finding, playbook_id="pb-test")
        assert session.version == 0
        session.version += 1
        assert session.version == 1

    def test_review_fields_in_batch_run(self) -> None:
        finding = _make_finding()
        session = RemediationSession(
            finding=finding,
            playbook_id="pb-test",
            review_status="approved",
            reviewed_by="alice",
            reviewed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        wave = Wave(wave_number=1, sessions=[session])
        batch = BatchRun(
            run_id="test-run",
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            waves=[wave],
            total_findings=1,
        )
        data = batch.model_dump(mode="json")
        s = data["waves"][0]["sessions"][0]
        assert s["review_status"] == "approved"
        assert s["reviewed_by"] == "alice"


class TestServiceOverrides:
    """Test service overrides loading and prompt injection."""

    def test_load_overrides_missing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "orchestrator.devin.session_manager._SERVICE_OVERRIDES_PATH",
            tmp_path / "nonexistent.json",
        )
        result = load_service_overrides()
        assert result == {}

    def test_load_overrides_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        overrides = {"payment-service": {"test_command": "mvn test"}}
        overrides_path = tmp_path / "overrides.json"
        overrides_path.write_text(json.dumps(overrides))
        monkeypatch.setattr(
            "orchestrator.devin.session_manager._SERVICE_OVERRIDES_PATH",
            overrides_path,
        )
        result = load_service_overrides()
        assert result["payment-service"]["test_command"] == "mvn test"

    def test_load_overrides_corrupt_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        overrides_path = tmp_path / "corrupt.json"
        overrides_path.write_text("{{invalid json")
        monkeypatch.setattr(
            "orchestrator.devin.session_manager._SERVICE_OVERRIDES_PATH",
            overrides_path,
        )
        result = load_service_overrides()
        assert result == {}

    def test_prompt_includes_overrides(self) -> None:
        finding = _make_finding(
            service_name="payment-service", file_path="test.java"
        )
        overrides = {
            "payment-service": {
                "test_command": "mvn test",
                "branch_prefix": "security/payment",
                "deployment_notes": "PCI zone",
                "custom_instructions": "Run integration tests",
            }
        }
        prompt = build_remediation_prompt(finding, service_overrides=overrides)
        assert "mvn test" in prompt
        assert "security/payment" in prompt
        assert "PCI zone" in prompt
        assert "Run integration tests" in prompt
        assert "Service-Specific Instructions (payment-service)" in prompt

    def test_prompt_no_overrides_for_unknown_service(self) -> None:
        finding = _make_finding(service_name="unknown-svc")
        overrides = {"payment-service": {"test_command": "mvn test"}}
        prompt = build_remediation_prompt(finding, service_overrides=overrides)
        assert "Service-Specific Instructions" not in prompt

    def test_prompt_without_overrides_param(self) -> None:
        finding = _make_finding()
        prompt = build_remediation_prompt(finding)
        assert "Service-Specific Instructions" not in prompt
        assert "Security Remediation Task" in prompt

    def test_prompt_with_memory_and_overrides(self) -> None:
        finding = _make_finding(service_name="payment-service")
        overrides = {
            "payment-service": {
                "test_command": "mvn test",
                "branch_prefix": "security/payment",
            }
        }
        memory = "Previously fixed by upgrading dependency."
        prompt = build_remediation_prompt(
            finding, memory_context=memory, service_overrides=overrides
        )
        assert "Service-Specific Instructions" in prompt
        assert "Prior Remediation Knowledge" in prompt
        assert "mvn test" in prompt
        assert "Previously fixed" in prompt

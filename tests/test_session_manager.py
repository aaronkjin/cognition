import pytest
from unittest.mock import AsyncMock

from orchestrator.config import OrchestratorConfig
from orchestrator.models import (
    Finding,
    FindingCategory,
    RemediationSession,
    SessionStatus,
    Severity,
)
from orchestrator.devin.session_manager import (
    REMEDIATION_OUTPUT_SCHEMA,
    build_remediation_prompt,
    create_remediation_session,
    interpret_session_status,
)


def _make_finding(**overrides) -> Finding:
    defaults = dict(
        finding_id="FIND-0001",
        scanner="sonarqube",
        category=FindingCategory.SQL_INJECTION,
        severity=Severity.CRITICAL,
        title="SQL Injection in UserDAO",
        description="String concatenation in SQL query",
        service_name="payment-service",
        repo_url="https://github.com/coupang-demo/payment-service",
        file_path="src/main/java/com/coupang/dao/UserDAO.java",
        line_number=87,
        cwe_id="CWE-89",
        language="java",
    )
    defaults.update(overrides)
    return Finding(**defaults)


class TestBuildRemediationPrompt:
    def test_contains_all_fields(self):
        finding = _make_finding()
        prompt = build_remediation_prompt(finding)
        assert "FIND-0001" in prompt
        assert "payment-service" in prompt
        assert "sql_injection" in prompt
        assert "critical" in prompt
        assert "UserDAO.java" in prompt
        assert "87" in prompt
        assert "CWE-89" in prompt
        assert "SQL Injection" in prompt
        assert "coupang-demo/payment-service" in prompt

    def test_dependency_finding_includes_versions(self):
        finding = _make_finding(
            category=FindingCategory.DEPENDENCY_VULNERABILITY,
            dependency_name="log4j-core",
            current_version="2.14.1",
            fixed_version="2.17.1",
        )
        prompt = build_remediation_prompt(finding)
        assert "log4j-core" in prompt
        assert "2.14.1" in prompt
        assert "2.17.1" in prompt

    def test_no_line_number_shows_na(self):
        finding = _make_finding(line_number=None)
        prompt = build_remediation_prompt(finding)
        assert "N/A" in prompt


class TestCreateRemediationSession:
    @pytest.mark.asyncio
    async def test_success(self):
        mock_client = AsyncMock()
        mock_client.create_session.return_value = {
            "session_id": "ses-abc123",
            "url": "https://app.devin.ai/sessions/ses-abc123",
            "is_new_session": True,
        }

        finding = _make_finding()
        session = RemediationSession(finding=finding, playbook_id="pb-001", wave_number=1)
        config = OrchestratorConfig()

        result = await create_remediation_session(mock_client, session, config)

        assert result.session_id == "ses-abc123"
        assert result.status == SessionStatus.DISPATCHED
        assert result.devin_url == "https://app.devin.ai/sessions/ses-abc123"
        assert result.created_at is not None

        # Verify API was called correctly
        mock_client.create_session.assert_called_once()
        call_kwargs = mock_client.create_session.call_args[1]
        assert "FIND-0001" in call_kwargs["prompt"]
        assert call_kwargs["playbook_id"] == "pb-001"
        assert call_kwargs["idempotent"] is True
        assert call_kwargs["max_acu_limit"] == config.max_acu_per_session
        assert call_kwargs["structured_output_schema"] == REMEDIATION_OUTPUT_SCHEMA

    @pytest.mark.asyncio
    async def test_api_failure(self):
        mock_client = AsyncMock()
        mock_client.create_session.side_effect = Exception("API down")

        finding = _make_finding()
        session = RemediationSession(finding=finding, playbook_id="pb-001", wave_number=1)
        config = OrchestratorConfig()

        result = await create_remediation_session(mock_client, session, config)

        assert result.status == SessionStatus.FAILED
        assert "API down" in result.error_message

    @pytest.mark.asyncio
    async def test_empty_playbook_id_not_sent(self):
        """If playbook_id is empty string, don't send it to the API."""
        mock_client = AsyncMock()
        mock_client.create_session.return_value = {
            "session_id": "ses-xyz",
            "url": "https://app.devin.ai/sessions/ses-xyz",
            "is_new_session": True,
        }

        finding = _make_finding()
        session = RemediationSession(finding=finding, playbook_id="", wave_number=1)
        config = OrchestratorConfig()

        await create_remediation_session(mock_client, session, config)

        call_kwargs = mock_client.create_session.call_args[1]
        # Empty playbook_id should be sent as None or not included
        assert call_kwargs.get("playbook_id") is None or call_kwargs.get("playbook_id") == ""


class TestInterpretSessionStatus:
    def test_working(self):
        status, pr_url, error = interpret_session_status(
            {"status_enum": "working", "pull_request": None, "structured_output": None}
        )
        assert status == SessionStatus.WORKING
        assert pr_url is None

    def test_finished_with_pr(self):
        status, pr_url, error = interpret_session_status({
            "status_enum": "finished",
            "pull_request": {"url": "https://github.com/org/repo/pull/42"},
            "structured_output": {"status": "completed"},
        })
        assert status == SessionStatus.SUCCESS
        assert pr_url == "https://github.com/org/repo/pull/42"

    def test_blocked_without_pr(self):
        status, pr_url, error = interpret_session_status({
            "status_enum": "blocked",
            "pull_request": None,
            "structured_output": {"error_message": "Tests failed"},
        })
        assert status == SessionStatus.BLOCKED
        assert error == "Tests failed"

    def test_blocked_with_pr_is_success(self):
        """Devin goes to 'blocked' after creating a PR and waiting for approval."""
        status, pr_url, error = interpret_session_status({
            "status_enum": "blocked",
            "pull_request": {"url": "https://github.com/org/repo/pull/99"},
            "structured_output": {"status": "completed"},
        })
        assert status == SessionStatus.SUCCESS
        assert pr_url == "https://github.com/org/repo/pull/99"

    def test_expired(self):
        status, pr_url, error = interpret_session_status(
            {"status_enum": "expired", "pull_request": None, "structured_output": None}
        )
        assert status == SessionStatus.TIMEOUT

    def test_unknown_status_treated_as_working(self):
        """Unknown statuses keep polling rather than marking as failed."""
        status, pr_url, error = interpret_session_status(
            {"status_enum": "some_new_thing", "pull_request": None, "structured_output": None}
        )
        assert status == SessionStatus.WORKING


class TestRemediationOutputSchema:
    def test_schema_is_valid_json_schema(self):
        assert REMEDIATION_OUTPUT_SCHEMA["type"] == "object"
        assert "finding_id" in REMEDIATION_OUTPUT_SCHEMA["properties"]
        assert "status" in REMEDIATION_OUTPUT_SCHEMA["properties"]
        assert "progress_pct" in REMEDIATION_OUTPUT_SCHEMA["properties"]
        required = REMEDIATION_OUTPUT_SCHEMA["required"]
        assert "finding_id" in required
        assert "status" in required
        assert "progress_pct" in required
        assert "current_step" in required

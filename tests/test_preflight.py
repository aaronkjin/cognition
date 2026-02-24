import pytest
from unittest.mock import AsyncMock, patch

from orchestrator.config import OrchestratorConfig
from orchestrator.models import Finding, FindingCategory, Severity
from orchestrator.preflight import preflight_check, _check_playbooks


def _make_finding(**overrides):
    defaults = {
        "finding_id": "FIND-TEST",
        "scanner": "test",
        "category": FindingCategory.SQL_INJECTION,
        "severity": Severity.HIGH,
        "title": "Test Finding",
        "description": "A test",
        "service_name": "test-service",
        "repo_url": "https://github.com/test/repo",
        "file_path": "test.py",
    }
    defaults.update(overrides)
    return Finding(**defaults)


@pytest.mark.asyncio
async def test_preflight_mock_mode_passes():
    config = OrchestratorConfig(mock_mode=True)
    client = AsyncMock()
    findings = [_make_finding()]
    errors = await preflight_check(client, config, findings)
    assert errors == []


@pytest.mark.asyncio
async def test_preflight_mock_mode_no_findings():
    config = OrchestratorConfig(mock_mode=True)
    client = AsyncMock()
    errors = await preflight_check(client, config, [])
    assert len(errors) == 1
    assert "No findings" in errors[0]


@pytest.mark.asyncio
async def test_preflight_live_no_api_key():
    config = OrchestratorConfig(mock_mode=False, devin_api_key="")
    client = AsyncMock()
    findings = [_make_finding()]
    errors = await preflight_check(client, config, findings)
    assert any("DEVIN_API_KEY" in e for e in errors)


@pytest.mark.asyncio
async def test_preflight_live_api_unreachable():
    config = OrchestratorConfig(mock_mode=False, devin_api_key="test-key")
    client = AsyncMock()
    client.list_sessions.side_effect = Exception("Connection refused")
    findings = [_make_finding()]
    errors = await preflight_check(client, config, findings)
    assert any("Cannot reach" in e for e in errors)


@pytest.mark.asyncio
async def test_preflight_live_api_reachable():
    config = OrchestratorConfig(mock_mode=False, devin_api_key="test-key")
    client = AsyncMock()
    client.list_sessions.return_value = {"sessions": [], "total": 0}
    findings = [_make_finding()]
    errors = await preflight_check(client, config, findings)
    assert errors == []


@pytest.mark.asyncio
async def test_preflight_hybrid_no_repos():
    config = OrchestratorConfig(
        mock_mode=False, hybrid_mode=True, connected_repos=[], devin_api_key="test"
    )
    client = AsyncMock()
    client.list_sessions.return_value = {"sessions": [], "total": 0}
    findings = [_make_finding()]
    errors = await preflight_check(client, config, findings)
    assert any("CONNECTED_REPOS" in e for e in errors)


@pytest.mark.asyncio
async def test_preflight_hybrid_with_repos():
    config = OrchestratorConfig(
        mock_mode=False, hybrid_mode=True,
        connected_repos=["payment-service"], devin_api_key="test",
    )
    client = AsyncMock()
    client.list_sessions.return_value = {"sessions": [], "total": 0}
    findings = [_make_finding()]
    errors = await preflight_check(client, config, findings)
    assert errors == []


# --- Playbook preflight tests ---

def test_check_playbooks_existing_categories():
    """Known categories with real playbook files on disk should pass."""
    findings = [_make_finding(category=FindingCategory.SQL_INJECTION)]
    errors = _check_playbooks(findings)
    assert errors == []


def test_check_playbooks_missing_file():
    """A category whose playbook path doesn't exist on disk should error."""
    findings = [_make_finding(category=FindingCategory.SQL_INJECTION)]
    with patch(
        "orchestrator.planner.playbook_selector.get_playbook_path",
        return_value="playbooks/nonexistent.devin.md",
    ):
        errors = _check_playbooks(findings)
    assert len(errors) == 1
    assert "nonexistent.devin.md" in errors[0]


def test_check_playbooks_deduplicates_categories():
    """Multiple findings of the same category should only check once."""
    findings = [
        _make_finding(finding_id="FIND-001", category=FindingCategory.SQL_INJECTION),
        _make_finding(finding_id="FIND-002", category=FindingCategory.SQL_INJECTION),
    ]
    with patch(
        "orchestrator.planner.playbook_selector.get_playbook_path",
        return_value="playbooks/nonexistent.devin.md",
    ):
        errors = _check_playbooks(findings)
    # Only one error even though two findings share the category
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_preflight_mock_mode_catches_missing_playbook():
    """Even in mock mode, missing playbook files should be reported."""
    config = OrchestratorConfig(mock_mode=True)
    client = AsyncMock()
    findings = [_make_finding()]
    with patch(
        "orchestrator.planner.playbook_selector.get_playbook_path",
        return_value="playbooks/nonexistent.devin.md",
    ):
        errors = await preflight_check(client, config, findings)
    assert any("Playbook file missing" in e for e in errors)

from orchestrator.devin.session_manager import determine_data_source
from orchestrator.config import OrchestratorConfig
from orchestrator.models import Finding, FindingCategory, Severity


def _make_finding(service_name: str = "payment-service") -> Finding:
    return Finding(
        finding_id="FIND-TEST",
        scanner="test",
        category=FindingCategory.SQL_INJECTION,
        severity=Severity.HIGH,
        title="Test",
        description="Test",
        service_name=service_name,
        repo_url="https://github.com/test/repo",
        file_path="test.py",
    )


def test_mock_mode_returns_mock():
    config = OrchestratorConfig(mock_mode=True)
    assert determine_data_source(_make_finding(), config) == "mock"


def test_live_mode_returns_live():
    config = OrchestratorConfig(mock_mode=False, hybrid_mode=False)
    assert determine_data_source(_make_finding(), config) == "live"


def test_hybrid_connected_repo_returns_live():
    config = OrchestratorConfig(
        mock_mode=False, hybrid_mode=True,
        connected_repos=["coupang-payment-service"],
    )
    assert determine_data_source(_make_finding("payment-service"), config) == "live"


def test_hybrid_unconnected_repo_returns_mock():
    config = OrchestratorConfig(
        mock_mode=False, hybrid_mode=True,
        connected_repos=["coupang-payment-service"],
    )
    assert determine_data_source(_make_finding("unknown-service"), config) == "mock"


def test_hybrid_exact_match_returns_live():
    config = OrchestratorConfig(
        mock_mode=False, hybrid_mode=True,
        connected_repos=["payment-service"],
    )
    assert determine_data_source(_make_finding("payment-service"), config) == "live"


def test_hybrid_multiple_repos():
    config = OrchestratorConfig(
        mock_mode=False, hybrid_mode=True,
        connected_repos=["coupang-payment-service", "coupang-user-service"],
    )
    assert determine_data_source(_make_finding("payment-service"), config) == "live"
    assert determine_data_source(_make_finding("user-service"), config) == "live"
    assert determine_data_source(_make_finding("catalog-service"), config) == "mock"


def test_hybrid_empty_repos_returns_mock():
    config = OrchestratorConfig(
        mock_mode=False, hybrid_mode=True,
        connected_repos=[],
    )
    assert determine_data_source(_make_finding(), config) == "mock"

from click.testing import CliRunner

from orchestrator.main import cli


def test_ingest_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["ingest", "sample_data/findings.csv"])
    assert result.exit_code == 0
    assert "20" in result.output or "findings" in result.output.lower()


def test_plan_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["plan", "sample_data/findings.csv", "--wave-size", "5"])
    assert result.exit_code == 0
    assert "wave" in result.output.lower()


def test_dry_run():
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "sample_data/findings.csv", "--wave-size", "5", "--dry-run"])
    assert result.exit_code == 0
    assert "dry" in result.output.lower() or "FIND-" in result.output


def test_status_no_state():
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    # Should handle missing state.json gracefully

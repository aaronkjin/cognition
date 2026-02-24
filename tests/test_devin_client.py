import asyncio
import time

import pytest

from mock.mock_devin_client import MockDevinClient


@pytest.mark.asyncio
async def test_mock_create_and_get_session():
    """Create a session and verify it progresses through stages."""
    client = MockDevinClient(seed=42)
    result = await client.create_session(
        prompt="Fix finding FIND-0001: SQL Injection in payment-service TransactionDAO.java",
        playbook_id="pb-sql-injection",
        tags=["wave-1", "sql_injection", "payment-service"],
        max_acu_limit=5,
    )
    assert "session_id" in result
    assert result["session_id"].startswith("mock-")
    assert result["is_new_session"] is True

    # Immediately after creation, should be in analyzing stage
    details = await client.get_session(result["session_id"])
    assert details["status_enum"] == "working"
    assert details["structured_output"]["status"] == "analyzing"
    assert details["structured_output"]["progress_pct"] >= 0

    await client.close()


@pytest.mark.asyncio
async def test_mock_idempotent_session():
    """Same prompt with idempotent=True should return same session."""
    client = MockDevinClient(seed=42)
    prompt = "Fix FIND-0001"
    r1 = await client.create_session(prompt=prompt, idempotent=True)
    r2 = await client.create_session(prompt=prompt, idempotent=True)
    assert r1["session_id"] == r2["session_id"]
    assert r2["is_new_session"] is False
    await client.close()


@pytest.mark.asyncio
async def test_mock_session_completes():
    """After enough time, a successful session should reach 'finished'."""
    client = MockDevinClient(seed=42)
    result = await client.create_session(prompt="Fix FIND-0002: dependency vuln")

    # Fast-forward by manipulating the creation time
    sid = result["session_id"]
    client._sessions[sid]["created_at"] -= 120  # Jump 120 seconds into the future

    details = await client.get_session(sid)
    assert details["status_enum"] == "finished"
    assert details["structured_output"]["status"] == "completed"
    assert details["structured_output"]["progress_pct"] == 100
    assert details["pull_request"] is not None
    assert "url" in details["pull_request"]
    await client.close()


@pytest.mark.asyncio
async def test_mock_list_sessions_with_tags():
    """List sessions filtered by tags."""
    client = MockDevinClient(seed=42)
    await client.create_session(prompt="Fix A", tags=["wave-1", "sql_injection"])
    await client.create_session(prompt="Fix B", tags=["wave-1", "dependency"])
    await client.create_session(prompt="Fix C", tags=["wave-2", "sql_injection"])

    result = await client.list_sessions(tags=["wave-1"])
    assert result["total"] == 2

    result = await client.list_sessions(tags=["wave-1", "sql_injection"])
    assert result["total"] == 1

    result = await client.list_sessions()
    assert result["total"] == 3
    await client.close()


@pytest.mark.asyncio
async def test_mock_terminate_session():
    """Terminated session should show as blocked/failed."""
    client = MockDevinClient(seed=42)
    result = await client.create_session(prompt="Fix FIND-0003")
    await client.terminate_session(result["session_id"])

    details = await client.get_session(result["session_id"])
    # After termination, session should not be "working"
    assert details["status_enum"] in ("blocked", "finished")
    await client.close()


@pytest.mark.asyncio
async def test_mock_playbooks():
    """Create and list playbooks."""
    client = MockDevinClient(seed=42)
    pb = await client.create_playbook(title="SQL Injection Fix", body="# Steps\n...")
    assert "playbook_id" in pb
    assert pb["playbook_id"].startswith("pb-mock-")

    pbs = await client.list_playbooks()
    assert len(pbs["playbooks"]) == 1
    assert pbs["playbooks"][0]["playbook_id"] == pb["playbook_id"]
    await client.close()


@pytest.mark.asyncio
async def test_mock_failure_rate():
    """With enough sessions, ~15% should fail."""
    client = MockDevinClient(seed=12345)
    n = 100
    for i in range(n):
        await client.create_session(prompt=f"Fix FIND-{i:04d}")

    # Fast-forward all sessions
    for sid, state in client._sessions.items():
        state["created_at"] -= 120

    failed = 0
    for sid in client._sessions:
        details = await client.get_session(sid)
        if details["status_enum"] == "blocked":
            failed += 1

    # Should be roughly 15% (allow 5-25% range for statistical variance)
    assert 5 <= failed <= 25, f"Expected ~15 failures, got {failed}"
    await client.close()


@pytest.mark.asyncio
async def test_devin_client_interface_parity():
    """Verify MockDevinClient has all the same public methods as DevinClient."""
    from orchestrator.devin.client import DevinClient
    from mock.mock_devin_client import MockDevinClient

    devin_methods = {m for m in dir(DevinClient) if not m.startswith("_")}
    mock_methods = {m for m in dir(MockDevinClient) if not m.startswith("_")}

    # Mock should have at least all the public methods of DevinClient
    missing = devin_methods - mock_methods
    assert not missing, f"MockDevinClient missing methods: {missing}"

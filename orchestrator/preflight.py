from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from orchestrator.config import OrchestratorConfig
from orchestrator.models import Finding

logger = logging.getLogger(__name__)


async def preflight_check(
    client: Any,
    config: OrchestratorConfig,
    findings: list[Finding],
) -> list[str]:
    """Run pre-dispatch validation checks.

    Returns a list of error messages. Empty list = all checks passed.

    Checks:
    1. API key is present and non-empty (skip in mock mode)
    2. Devin API is reachable: GET /sessions?limit=1 (skip in mock mode)
    3. Required playbook files exist on disk for all finding categories
    4. connected_repos is non-empty when hybrid_mode is True
    5. At least one finding exists
    """
    errors: list[str] = []

    if config.mock_mode:
        # Skip API checks in mock mode, but still verify playbooks + findings
        if not findings:
            errors.append("No findings to remediate")
            return errors
        errors.extend(_check_playbooks(findings))
        return errors

    # Check 1: API key
    if not config.devin_api_key:
        errors.append("DEVIN_API_KEY is not set")

    # Check 2: API connectivity
    if config.devin_api_key:
        try:
            await client.list_sessions(limit=1)
            logger.info("Preflight: Devin API is reachable")
        except Exception as exc:
            errors.append(f"Cannot reach Devin API: {exc}")

    # Check 3: Required playbooks exist
    if findings:
        errors.extend(_check_playbooks(findings))

    # Check 4: Hybrid mode requires connected_repos
    if config.hybrid_mode and not config.connected_repos:
        errors.append("CONNECTED_REPOS must be set when using --hybrid mode")

    # Check 5: Findings exist
    if not findings:
        errors.append("No findings to remediate")

    return errors


def _check_playbooks(findings: list[Finding]) -> list[str]:
    """Verify that playbook files exist on disk for all finding categories."""
    from orchestrator.planner.playbook_selector import get_playbook_path

    errors: list[str] = []
    categories_seen: set[str] = set()

    for finding in findings:
        cat_key = finding.category.value
        if cat_key in categories_seen:
            continue
        categories_seen.add(cat_key)

        playbook_path = get_playbook_path(finding.category)
        if not Path(playbook_path).exists():
            errors.append(
                f"Playbook file missing for category '{cat_key}': {playbook_path}"
            )

    if not errors:
        logger.info("Preflight: all required playbook files exist (%d categories)", len(categories_seen))

    return errors

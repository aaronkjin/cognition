from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass

from orchestrator.models import FindingCategory, Wave

logger = logging.getLogger(__name__)

# Category → playbook file path (relative to project root)
PLAYBOOK_MAP: dict[FindingCategory, str] = {
    FindingCategory.DEPENDENCY_VULNERABILITY: "playbooks/dependency_vulnerability.devin.md",
    FindingCategory.SQL_INJECTION: "playbooks/sql_injection.devin.md",
    FindingCategory.HARDCODED_SECRET: "playbooks/hardcoded_secrets.devin.md",
    FindingCategory.PII_LOGGING: "playbooks/pii_logging.devin.md",
    FindingCategory.MISSING_ENCRYPTION: "playbooks/missing_encryption.devin.md",
    FindingCategory.ACCESS_LOGGING: "playbooks/access_logging.devin.md",
}

# Fallback for categories without a dedicated playbook (XSS, PATH_TRAVERSAL, OTHER)
FALLBACK_PLAYBOOK: str = "playbooks/dependency_vulnerability.devin.md"


def get_playbook_path(category: FindingCategory) -> str:
    """Return the playbook file path for a finding category."""
    return PLAYBOOK_MAP.get(category, FALLBACK_PLAYBOOK)


async def ensure_playbooks_uploaded(client: Any) -> dict[str, str]:
    """Upload all playbooks to Devin if not already present.

    Returns: dict mapping playbook file path → playbook_id
    """
    # Get existing playbooks from the API
    # Real Devin API returns a list, mock returns {"playbooks": [...]}
    response = await client.list_playbooks()
    playbooks_list: list[dict[str, Any]] = (
        response if isinstance(response, list)
        else response.get("playbooks", [])
    )
    existing: dict[str, str] = {}
    for pb in playbooks_list:
        existing[pb["title"]] = pb["playbook_id"]

    # Deduplicate playbook paths
    unique_paths = sorted(set(PLAYBOOK_MAP.values()))
    path_to_id: dict[str, str] = {}

    for rel_path in unique_paths:
        title = Path(rel_path).stem  # e.g. "sql_injection.devin" → use full stem
        # Use a cleaner title: strip .devin from stem
        title = Path(rel_path).name.replace(".devin.md", "")

        # Check if already uploaded
        if title in existing:
            path_to_id[rel_path] = existing[title]
            logger.info("Playbook already exists: %s → %s", rel_path, existing[title])
            continue

        # Read file from disk
        file_path = Path(rel_path)
        if not file_path.exists():
            logger.warning("Playbook file not found on disk: %s", rel_path)
            continue

        body = file_path.read_text(encoding="utf-8")
        result = await client.create_playbook(title=title, body=body)
        playbook_id = result["playbook_id"]
        path_to_id[rel_path] = playbook_id
        logger.info("Uploaded playbook: %s → %s", rel_path, playbook_id)

    return path_to_id


def assign_playbooks(
    waves: list[Wave],
    playbook_ids: dict[str, str],
) -> list[Wave]:
    """Set playbook_id on each session based on its finding's category.

    Falls back to the first available playbook_id if no match. Mutates in place.
    """
    # Pre-compute a fallback ID in case a mapping is missing
    fallback_id: str | None = None
    if playbook_ids:
        fallback_id = next(iter(playbook_ids.values()))

    for wave in waves:
        for session in wave.sessions:
            path = get_playbook_path(session.finding.category)
            pb_id = playbook_ids.get(path)

            if pb_id is None:
                if fallback_id is not None:
                    logger.warning(
                        "No playbook_id for category %s (path %s), using fallback %s",
                        session.finding.category,
                        path,
                        fallback_id,
                    )
                    pb_id = fallback_id
                else:
                    logger.warning(
                        "No playbook_id available for category %s, leaving empty",
                        session.finding.category,
                    )
                    continue

            session.playbook_id = pb_id

    return waves

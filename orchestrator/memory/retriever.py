from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from orchestrator.memory.models import MemoryGraph, MemoryGraphEntry
from orchestrator.memory.store import MemoryStore
from orchestrator.models import Finding

logger = logging.getLogger(__name__)

# Scoring weights
_CATEGORY_MATCH_SCORE = 10.0
_SERVICE_MATCH_SCORE = 5.0
_SEVERITY_MATCH_SCORE = 2.0
_CONFIDENCE_SCORES = {"high": 3.0, "medium": 1.5, "low": 0.5}
_LIVE_SOURCE_BONUS = 2.0
_SUCCESS_BONUS = 3.0
_FRESHNESS_DECAY_DAYS = 30  # Score decays over this period


def retrieve_memories(
    finding: Finding,
    store: MemoryStore,
    max_results: int = 3,
    prefer_live: bool = True,
) -> list[dict[str, Any]]:
    """Retrieve ranked, relevant memories for a finding.

    Returns a list of dicts with:
    - content: str (markdown)
    - score: float
    - source_note: str (citation for prompt injection)
    - data_source: str
    """
    graph = store.load_graph()
    if not graph.entries:
        return []

    scored: list[tuple[float, MemoryGraphEntry]] = []

    for entry in graph.entries:
        score = _score_entry(entry, finding, prefer_live)
        if score > 0:
            scored.append((score, entry))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    results: list[dict[str, Any]] = []
    for score, entry in scored[:max_results]:
        content = store.load_item(entry.item_id)
        if content is None:
            continue

        source_note = f"[Memory from run {entry.run_id}, source: {entry.data_source}]"
        if entry.data_source == "mock" and prefer_live:
            source_note += (
                " (Note: this memory is from a mock session"
                " — actual behavior may differ)"
            )

        results.append(
            {
                "content": content,
                "score": score,
                "source_note": source_note,
                "data_source": entry.data_source,
            }
        )

    logger.info(
        "Retrieved %d memories for %s (category=%s, service=%s)",
        len(results),
        finding.finding_id,
        finding.category.value,
        finding.service_name,
    )
    return results


def _score_entry(
    entry: MemoryGraphEntry,
    finding: Finding,
    prefer_live: bool,
) -> float:
    """Score a memory entry's relevance to a finding."""
    score = 0.0

    # Category match (strongest signal)
    if entry.category == finding.category.value:
        score += _CATEGORY_MATCH_SCORE

    # Service match
    if entry.service_name == finding.service_name:
        score += _SERVICE_MATCH_SCORE

    # Zero relevance if neither category nor service matches
    if score == 0:
        return 0.0

    # Severity match (only applied after relevance gate)
    if entry.severity == finding.severity.value:
        score += _SEVERITY_MATCH_SCORE

    # Confidence bonus
    if entry.confidence:
        score += _CONFIDENCE_SCORES.get(entry.confidence, 0.0)

    # Live source bonus
    if prefer_live and entry.data_source == "live":
        score += _LIVE_SOURCE_BONUS

    # Success bonus (successful fixes are more useful)
    if entry.outcome == "success":
        score += _SUCCESS_BONUS

    # Freshness decay
    try:
        created = datetime.fromisoformat(entry.created_at)
        age_days = (datetime.now(timezone.utc) - created).days
        if age_days > 0:
            decay = max(0.0, 1.0 - (age_days / _FRESHNESS_DECAY_DAYS))
            score *= 0.5 + 0.5 * decay  # Decay reduces score by up to 50%
    except (ValueError, TypeError):
        pass  # Can't parse date, no decay applied

    return score

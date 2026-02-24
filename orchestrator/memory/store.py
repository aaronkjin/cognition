from __future__ import annotations

import json
import logging
from pathlib import Path

from orchestrator.memory.models import (
    MemoryGraph,
    MemoryGraphEntry,
    MemoryItem,
    MemoryRelationship,
)
from orchestrator.utils import atomic_write_json, with_file_lock

logger = logging.getLogger(__name__)

_DEFAULT_MEMORY_DIR = "orchestrator/memory"


class MemoryStore:
    """Filesystem-backed memory store.

    Stores:
    - graph.json: metadata-only index of all memory items
    - items/<item_id>.md: full narrative markdown for each item
    """

    def __init__(self, memory_dir: str | Path = _DEFAULT_MEMORY_DIR) -> None:
        self._dir = Path(memory_dir)
        self._graph_path = self._dir / "graph.json"
        self._items_dir = self._dir / "items"
        self._items_dir.mkdir(parents=True, exist_ok=True)

    def load_graph(self) -> MemoryGraph:
        """Load the memory graph from disk."""
        if not self._graph_path.exists():
            return MemoryGraph()
        try:
            data = json.loads(self._graph_path.read_text(encoding="utf-8"))
            return MemoryGraph.model_validate(data)
        except (json.JSONDecodeError, OSError, Exception) as exc:
            logger.warning("Could not load memory graph: %s", exc)
            return MemoryGraph()

    def save_graph(self, graph: MemoryGraph) -> None:
        """Save the memory graph atomically with file lock."""
        with with_file_lock(self._graph_path):
            atomic_write_json(self._graph_path, graph.model_dump(mode="json"))

    def save_item(self, item: MemoryItem) -> None:
        """Save a memory item as markdown."""
        md_path = self._items_dir / f"{item.item_id}.md"
        content = _render_markdown(item)
        md_path.write_text(content, encoding="utf-8")
        logger.debug("Saved memory item %s", item.item_id)

    def load_item(self, item_id: str) -> str | None:
        """Load a memory item's markdown content. Returns None if not found."""
        md_path = self._items_dir / f"{item_id}.md"
        if not md_path.exists():
            return None
        try:
            return md_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def upsert(self, item: MemoryItem, graph: MemoryGraph) -> MemoryGraph:
        """Add or update a memory item in the graph and save the markdown."""
        # Save markdown
        self.save_item(item)

        # Build graph entry (metadata only)
        entry = MemoryGraphEntry(
            item_id=item.item_id,
            finding_id=item.finding_id,
            category=item.category,
            service_name=item.service_name,
            severity=item.severity,
            data_source=item.data_source,
            outcome=item.outcome,
            confidence=item.confidence,
            fix_approach_summary=item.fix_approach[:100] if item.fix_approach else None,
            created_at=item.created_at,
            run_id=item.run_id,
        )

        # Build relationships to other items in the same category or service
        for existing in graph.entries:
            if existing.item_id == item.item_id:
                continue
            rels: list[MemoryRelationship] = []
            if existing.category == item.category:
                rels.append(
                    MemoryRelationship(
                        target_id=existing.item_id, relation_type="same_category"
                    )
                )
            if existing.service_name == item.service_name:
                rels.append(
                    MemoryRelationship(
                        target_id=existing.item_id, relation_type="same_service"
                    )
                )
            entry.relationships.extend(rels)

        # Upsert in graph
        found = False
        for i, e in enumerate(graph.entries):
            if e.item_id == entry.item_id:
                graph.entries[i] = entry
                found = True
                break
        if not found:
            graph.entries.append(entry)

        return graph


def _render_markdown(item: MemoryItem) -> str:
    """Render a MemoryItem as a markdown document."""
    outcome_emoji = "SUCCESS" if item.outcome == "success" else "FAILED"
    confidence_str = item.confidence or "unknown"
    files = (
        "\n".join(f"- `{f}`" for f in item.files_modified)
        if item.files_modified
        else "- None"
    )
    tests_str = (
        "Yes"
        if item.tests_passed
        else ("No" if item.tests_passed is False else "N/A")
    )

    return f"""# Memory: {item.finding_id} — {item.title}

## Metadata
- **Category**: {item.category}
- **Service**: {item.service_name}
- **Severity**: {item.severity}
- **Outcome**: {outcome_emoji}
- **Confidence**: {confidence_str}
- **Data Source**: {item.data_source}
- **Run ID**: {item.run_id}
- **Created**: {item.created_at}

## Fix Approach
{item.fix_approach or "No fix approach recorded."}

## Files Modified
{files}

## Test Results
- **Tests Passed**: {tests_str}
- **Tests Added**: {item.tests_added}

## PR
{item.pr_url or "No PR created."}

## Error
{item.error_message or "No errors."}
"""

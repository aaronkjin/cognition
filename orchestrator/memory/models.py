from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryRelationship(BaseModel):
    """A relationship between two memory items."""

    target_id: str
    relation_type: str  # "same_category", "same_service", "similar_fix"


class MemoryGraphEntry(BaseModel):
    """Metadata-only entry in graph.json (no full content)."""

    item_id: str
    finding_id: str
    category: str
    service_name: str
    severity: str
    data_source: str  # "live" | "mock"
    outcome: str  # "success" | "failed"
    confidence: str | None = None  # "high" | "medium" | "low"
    fix_approach_summary: str | None = None
    created_at: str
    run_id: str
    relationships: list[MemoryRelationship] = Field(default_factory=list)


class MemoryGraph(BaseModel):
    """The full graph.json structure — metadata index only."""

    version: int = 1
    entries: list[MemoryGraphEntry] = Field(default_factory=list)


class MemoryItem(BaseModel):
    """Full narrative memory item (stored as markdown in items/*.md)."""

    item_id: str
    finding_id: str
    category: str
    service_name: str
    severity: str
    title: str
    data_source: str
    outcome: str
    confidence: str | None = None
    fix_approach: str | None = None
    files_modified: list[str] = Field(default_factory=list)
    error_message: str | None = None
    tests_passed: bool | None = None
    tests_added: int = 0
    pr_url: str | None = None
    run_id: str
    created_at: str

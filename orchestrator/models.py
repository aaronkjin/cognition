from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingCategory(str, Enum):
    DEPENDENCY_VULNERABILITY = "dependency_vulnerability"
    SQL_INJECTION = "sql_injection"
    HARDCODED_SECRET = "hardcoded_secret"
    PII_LOGGING = "pii_logging"
    MISSING_ENCRYPTION = "missing_encryption"
    ACCESS_LOGGING = "access_logging"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    OTHER = "other"


class Finding(BaseModel):
    finding_id: str
    scanner: str
    category: FindingCategory
    severity: Severity
    title: str
    description: str
    service_name: str
    repo_url: str
    file_path: str
    line_number: int | None = None
    cwe_id: str | None = None
    dependency_name: str | None = None
    current_version: str | None = None
    fixed_version: str | None = None
    language: str | None = None
    priority_score: float = 0.0


class SessionStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    WORKING = "working"
    BLOCKED = "blocked"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class RemediationSession(BaseModel):
    session_id: str | None = None
    finding: Finding
    playbook_id: str
    status: SessionStatus = SessionStatus.PENDING
    devin_url: str | None = None
    pr_url: str | None = None
    structured_output: dict[str, Any] | None = None
    wave_number: int = 0
    attempt: int = 1
    created_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    data_source: str = "mock"  # "live" | "mock"
    version: int = 0
    # HITL review fields
    review_status: str | None = None  # "pending" | "approved" | "rejected" | None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_reason: str | None = None


class Wave(BaseModel):
    wave_number: int
    sessions: list[RemediationSession]
    status: str = "pending"
    success_count: int = 0
    failure_count: int = 0

    @property
    def total_count(self) -> int:
        return len(self.sessions)


class BatchRun(BaseModel):
    run_id: str
    started_at: datetime
    waves: list[Wave]
    total_findings: int
    completed: int = 0
    successful: int = 0
    failed: int = 0
    prs_created: int = 0
    status: str = "pending"  # pending, running, completed, paused
    data_source: str = "mock"  # "live" | "mock" | "hybrid"
    events: list[dict[str, Any]] = Field(default_factory=list)  # Timeline events for the dashboard

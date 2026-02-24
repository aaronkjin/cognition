from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from orchestrator.utils import atomic_write_json

logger = logging.getLogger(__name__)


class IdempotencyLedger:
    """Run-scoped ledger tracking session creation attempts.

    Keys: "{run_id}-{finding_id}-attempt-{attempt}"
    Values: {"session_id": str, "created_at": str}
    """

    def __init__(self, ledger_path: str | Path) -> None:
        self._path = Path(ledger_path)
        self._entries: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._entries = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning(
                    "Could not load idempotency ledger at %s, starting fresh",
                    self._path,
                )
                self._entries = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._path, self._entries)

    def make_key(self, run_id: str, finding_id: str, attempt: int) -> str:
        return f"{run_id}-{finding_id}-attempt-{attempt}"

    def lookup(self, key: str) -> dict[str, Any] | None:
        return self._entries.get(key)

    def record(self, key: str, session_id: str, created_at: str) -> None:
        self._entries[key] = {
            "session_id": session_id,
            "created_at": created_at,
        }
        self._save()
        logger.debug("Idempotency recorded: %s -> %s", key, session_id)

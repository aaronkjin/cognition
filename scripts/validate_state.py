#!/usr/bin/env python3
"""Validate a state.json file for correctness and consistency."""

import json
import sys
from pathlib import Path


def validate(state_path: str) -> list[str]:
    """Validate state.json and return a list of error messages (empty = passed)."""
    errors: list[str] = []
    path = Path(state_path)

    if not path.exists():
        return [f"File not found: {state_path}"]

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # Required top-level fields
    for field in ["run_id", "started_at", "waves", "total_findings", "status", "data_source"]:
        if field not in data:
            errors.append(f"Missing top-level field: {field}")

    if "waves" not in data:
        return errors

    # Validate data_source at run level
    ds = data.get("data_source")
    if ds not in ("live", "mock", "hybrid"):
        errors.append(f"Invalid run-level data_source: {ds}")

    # Check sessions
    session_ids: set[str] = set()
    finding_ids: set[str] = set()

    for wi, wave in enumerate(data["waves"]):
        if "sessions" not in wave:
            errors.append(f"Wave {wi}: missing 'sessions' field")
            continue

        for session in wave["sessions"]:
            sid = session.get("session_id")
            status = session.get("status", "pending")
            fid = session.get("finding", {}).get("finding_id", "?")

            # Session ID present for non-pending sessions
            if status not in ("pending",) and not sid:
                errors.append(f"Session {fid}: status={status} but no session_id")

            # Duplicate session ID check
            if sid:
                if sid in session_ids:
                    errors.append(f"Duplicate session_id: {sid}")
                session_ids.add(sid)

            if fid and fid != "?":
                finding_ids.add(fid)

            # data_source must be set
            session_ds = session.get("data_source")
            if session_ds not in ("live", "mock"):
                errors.append(f"Session {fid}: invalid data_source={session_ds}")

            # Status sanity
            valid_statuses = {
                "pending", "dispatched", "working", "blocked",
                "success", "failed", "timeout",
            }
            if status not in valid_statuses:
                errors.append(f"Session {fid}: invalid status={status}")

            # Orphan check: completed session should have completed_at
            if status in ("success", "failed", "timeout") and not session.get("completed_at"):
                errors.append(f"Session {fid}: terminal status={status} but no completed_at")

    # total_findings consistency
    total = data.get("total_findings", 0)
    if total != len(finding_ids) and len(finding_ids) > 0:
        errors.append(
            f"total_findings={total} but found {len(finding_ids)} unique finding IDs"
        )

    return errors


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "state.json"
    errors = validate(path)

    if errors:
        print(f"VALIDATION FAILED ({len(errors)} errors):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")


if __name__ == "__main__":
    main()

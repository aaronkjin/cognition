from __future__ import annotations

import json
import os
import socket
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator


class FileLockTimeout(Exception):
    """Raised when a file lock cannot be acquired within the timeout."""


@contextmanager
def with_file_lock(
    target_path: str | Path,
    timeout_seconds: float = 5.0,
    poll_interval: float = 0.1,
    stale_timeout: float = 30.0,
    writer: str = "orchestrator",
) -> Generator[None, None, None]:
    """Cross-process file lock using exclusive file creation.

    Creates a <target>.lock sibling file. Compatible with the Node.js
    implementation in dashboard/lib/file-lock.ts (same protocol).

    Args:
        target_path: The file being protected (lock file will be <target>.lock).
        timeout_seconds: Max time to wait for lock acquisition.
        poll_interval: Seconds between retry attempts.
        stale_timeout: Force-remove lock if older than this AND owner is dead.
        writer: Identifier for the lock owner (for debugging).
    """
    lock_path = Path(str(target_path) + ".lock")
    deadline = time.monotonic() + timeout_seconds
    acquired = False

    try:
        while time.monotonic() < deadline:
            try:
                # O_CREAT | O_EXCL = atomic create-if-not-exists
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                # Write metadata for stale detection
                metadata = json.dumps({
                    "pid": os.getpid(),
                    "host": socket.gethostname(),
                    "started_at": time.time(),
                    "writer": writer,
                })
                os.write(fd, metadata.encode())
                os.close(fd)
                acquired = True
                break
            except FileExistsError:
                # Lock exists — check if stale
                if _is_stale_lock(lock_path, stale_timeout):
                    try:
                        os.unlink(str(lock_path))
                        continue  # Retry immediately after removing stale lock
                    except OSError:
                        pass  # Another process beat us to it
                time.sleep(poll_interval)

        if not acquired:
            raise FileLockTimeout(
                f"Could not acquire lock on {target_path} within {timeout_seconds}s"
            )

        yield
    finally:
        if acquired:
            try:
                os.unlink(str(lock_path))
            except OSError:
                pass  # Lock already removed (shouldn't happen, but be safe)


def _is_stale_lock(lock_path: Path, stale_timeout: float) -> bool:
    """Check if a lock file is stale (owner dead + age exceeded)."""
    try:
        content = lock_path.read_text(encoding="utf-8")
        meta = json.loads(content)
        age = time.time() - meta.get("started_at", 0)
        if age < stale_timeout:
            return False
        # Age exceeded — check if owner process is dead (same host only)
        owner_pid = meta.get("pid")
        owner_host = meta.get("host")
        if owner_host == socket.gethostname() and owner_pid:
            try:
                os.kill(owner_pid, 0)  # Signal 0 = check if process exists
                return False  # Process still alive
            except ProcessLookupError:
                return True  # Process dead + age exceeded
            except PermissionError:
                return False  # Process exists but we can't signal it
        # Different host or no PID — only use age
        return age > stale_timeout
    except (OSError, json.JSONDecodeError, KeyError):
        # Can't read metadata — treat as stale if file is old enough
        try:
            stat = lock_path.stat()
            return (time.time() - stat.st_mtime) > stale_timeout
        except OSError:
            return False


def atomic_write_json(path: str | Path, data: Any) -> None:
    """Write JSON atomically via temp file + rename.

    This prevents partial reads if another process reads during write.
    """
    path = Path(path)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )
    os.rename(str(tmp_path), str(path))

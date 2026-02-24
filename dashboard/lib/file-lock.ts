/**
 * Cross-process file lock using exclusive file creation.
 * Protocol-compatible with orchestrator/utils.py with_file_lock().
 */

import { open, unlink, readFile, stat } from "fs/promises";
import { hostname } from "os";
import { constants } from "fs";

export class FileLockTimeout extends Error {
  constructor(path: string, timeoutMs: number) {
    super(`Could not acquire lock on ${path} within ${timeoutMs}ms`);
    this.name = "FileLockTimeout";
  }
}

interface LockMetadata {
  pid: number;
  host: string;
  started_at: number;
  writer: string;
}

async function isStaleLock(
  lockPath: string,
  staleTimeoutMs: number,
): Promise<boolean> {
  try {
    const content = await readFile(lockPath, "utf-8");
    const meta: LockMetadata = JSON.parse(content);
    const ageMs = Date.now() - meta.started_at * 1000;
    if (ageMs < staleTimeoutMs) return false;

    // Can't reliably check PID from Node.js cross-platform,
    // so we rely on age-based staleness only.
    // The Python side does PID checks for same-host scenarios.
    return true;
  } catch {
    // Can't read metadata — check file age
    try {
      const stats = await stat(lockPath);
      return Date.now() - stats.mtimeMs > staleTimeoutMs;
    } catch {
      return false;
    }
  }
}

export async function withFileLock<T>(
  targetPath: string,
  fn: () => Promise<T>,
  options?: {
    timeoutMs?: number;
    pollIntervalMs?: number;
    staleTimeoutMs?: number;
    writer?: string;
  },
): Promise<T> {
  const {
    timeoutMs = 5000,
    pollIntervalMs = 100,
    staleTimeoutMs = 30000,
    writer = "dashboard",
  } = options ?? {};

  const lockPath = `${targetPath}.lock`;
  const deadline = Date.now() + timeoutMs;
  let acquired = false;

  try {
    while (Date.now() < deadline) {
      try {
        // O_CREAT | O_EXCL = atomic create-if-not-exists
        const fd = await open(
          lockPath,
          constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY,
        );
        const metadata: LockMetadata = {
          pid: process.pid,
          host: hostname(),
          started_at: Date.now() / 1000,
          writer,
        };
        await fd.writeFile(JSON.stringify(metadata));
        await fd.close();
        acquired = true;
        break;
      } catch (err: unknown) {
        if (
          err instanceof Error &&
          "code" in err &&
          (err as NodeJS.ErrnoException).code === "EEXIST"
        ) {
          // Lock exists — check if stale
          if (await isStaleLock(lockPath, staleTimeoutMs)) {
            try {
              await unlink(lockPath);
              continue;
            } catch {
              // Another process removed it
            }
          }
          await new Promise((r) => setTimeout(r, pollIntervalMs));
        } else {
          throw err;
        }
      }
    }

    if (!acquired) {
      throw new FileLockTimeout(targetPath, timeoutMs);
    }

    return await fn();
  } finally {
    if (acquired) {
      try {
        await unlink(lockPath);
      } catch {
        // Already removed
      }
    }
  }
}

"""One-command demo runner for Loom recording.

Usage:
    python scripts/demo.py

What it does:
1. Cleans up any existing state.json
2. Runs the orchestrator in mock mode with a small wave-size (5)
   and reduced poll interval (3 seconds) for faster demo flow
3. Prints instructions for starting the dashboard
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent.parent
    state_file = project_root / "state.json"

    # Clean previous state
    if state_file.exists():
        state_file.unlink()
        print("Cleaned previous state.json")

    # Set environment for fast demo
    env = os.environ.copy()
    env["MOCK_MODE"] = "true"
    env["POLL_INTERVAL_SECONDS"] = "3"
    env["WAVE_SIZE"] = "5"
    env["MAX_PARALLEL_SESSIONS"] = "10"
    env["STATE_FILE_PATH"] = str(state_file)

    csv_path = project_root / "sample_data" / "findings.csv"

    print("=" * 60)
    print("  Coupang Security Remediation — Demo Mode")
    print("=" * 60)
    print()
    print("  Dashboard: cd dashboard && npm run dev")
    print("  Open: http://localhost:3000")
    print()
    print("  Starting orchestrator in mock mode...")
    print("=" * 60)
    print()

    # Run the orchestrator
    subprocess.run(
        [
            sys.executable, "-m", "orchestrator.main",
            "run", str(csv_path),
            "--wave-size", "5",
        ],
        cwd=str(project_root),
        env=env,
    )


if __name__ == "__main__":
    main()

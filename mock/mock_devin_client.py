from __future__ import annotations

import logging
import random
import re
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Stage definitions: (name, min_duration_s, max_duration_s, progress_start, progress_end)
_STAGES = [
    ("analyzing", 5, 10, 0, 25),
    ("fixing", 10, 20, 25, 60),
    ("testing", 8, 15, 60, 85),
    ("creating_pr", 3, 8, 85, 95),
]

# Fix approaches per category
_FIX_APPROACHES: dict[str, str] = {
    "sql_injection": "Replace string concatenation in SQL query with parameterized query using PreparedStatement",
    "dependency_vulnerability": "Upgrade vulnerable dependency to the patched version specified in the advisory",
    "hardcoded_secret": "Move hardcoded credential to environment variable and load via application config",
    "pii_logging": "Redact PII fields (email, phone, SSN) from log output using a sanitization filter",
    "missing_encryption": "Add AES-256 encryption for sensitive data at rest using a managed key store",
    "access_logging": "Add structured audit logging middleware to capture access events for compliance",
    "xss": "Apply context-aware output encoding using the framework's built-in HTML escaping utilities",
    "path_traversal": "Validate and canonicalize file paths against a whitelist of allowed directories",
}

# File path templates per category
_FILE_TEMPLATES: dict[str, list[str]] = {
    "sql_injection": [
        "src/main/java/com/coupang/{service}/dao/{cls}.java",
        "src/main/java/com/coupang/{service}/dao/{cls}Test.java",
    ],
    "dependency_vulnerability": ["pom.xml", "requirements.txt", "package.json"],
    "hardcoded_secret": [
        "src/main/java/com/coupang/{service}/config/{cls}.java",
        "config.py",
    ],
    "pii_logging": [
        "app/routes/{service}_routes.py",
        "src/middleware/logging.ts",
    ],
    "missing_encryption": [
        "src/main/java/com/coupang/{service}/model/{cls}.java",
        "app/models/{service}.py",
    ],
    "access_logging": [
        "src/middleware/auth.ts",
        "src/main/java/com/coupang/{service}/controller/{cls}.java",
    ],
    "xss": [
        "src/controllers/{service}Controller.ts",
    ],
    "path_traversal": [
        "src/controllers/fileController.ts",
    ],
}


def _extract_finding_id(prompt: str) -> str:
    """Extract a finding ID like FIND-0001 from a prompt string."""
    match = re.search(r"FIND-\d+", prompt)
    return match.group(0) if match else "FIND-UNKNOWN"


def _extract_category(prompt: str, tags: list[str] | None) -> str:
    """Best-effort extraction of finding category from prompt or tags."""
    known = list(_FIX_APPROACHES.keys())
    if tags:
        for tag in tags:
            if tag in known:
                return tag
    for cat in known:
        if cat in prompt.lower().replace(" ", "_"):
            return cat
    return "other"


def _extract_service(prompt: str, tags: list[str] | None) -> str:
    """Best-effort extraction of service name from prompt or tags."""
    match = re.search(r"([\w-]+-service)", prompt)
    if match:
        return match.group(1)
    if tags:
        for tag in tags:
            if tag.endswith("-service"):
                return tag
    return "unknown-service"


class MockDevinClient:
    """Simulates the Devin API with realistic timing and state transitions.

    Sessions progress through stages based on elapsed wall-clock time:
      analyzing (5-10s) -> fixing (10-20s) -> testing (8-15s) -> creating_pr (3-8s) -> completed

    ~85% of sessions succeed. ~15% fail (get stuck at 'testing' with status 'blocked').
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._sessions: dict[str, dict[str, Any]] = {}
        self._playbooks: dict[str, dict[str, Any]] = {}

    async def create_session(
        self,
        prompt: str,
        playbook_id: str | None = None,
        tags: list[str] | None = None,
        structured_output_schema: dict[str, Any] | None = None,
        max_acu_limit: int | None = None,
        idempotent: bool = True,
    ) -> dict[str, Any]:
        """Create a mock session. Returns immediately with a fake session_id."""
        # Idempotent check: return existing session with the same prompt
        if idempotent:
            for sid, state in self._sessions.items():
                if state["prompt"] == prompt:
                    logger.debug("Idempotent hit for prompt: %s", prompt[:60])
                    return {
                        "session_id": sid,
                        "url": f"https://app.devin.ai/sessions/{sid}",
                        "is_new_session": False,
                    }

        session_id = f"mock-{uuid.uuid4().hex[:8]}"
        will_fail = self._rng.random() < 0.15
        finding_id = _extract_finding_id(prompt)
        category = _extract_category(prompt, tags)
        service = _extract_service(prompt, tags)

        # Randomized stage durations within spec ranges
        stage_durations: list[tuple[str, float, int, int]] = []
        for name, min_dur, max_dur, p_start, p_end in _STAGES:
            dur = self._rng.uniform(min_dur, max_dur)
            stage_durations.append((name, dur, p_start, p_end))

        self._sessions[session_id] = {
            "session_id": session_id,
            "created_at": time.time(),
            "will_fail": will_fail,
            "stage_durations": stage_durations,
            "prompt": prompt,
            "playbook_id": playbook_id,
            "tags": tags or [],
            "finding_id": finding_id,
            "category": category,
            "service": service,
            "terminated": False,
        }

        logger.info(
            "Mock session created: %s (will_fail=%s, finding=%s)",
            session_id,
            will_fail,
            finding_id,
        )

        return {
            "session_id": session_id,
            "url": f"https://app.devin.ai/sessions/{session_id}",
            "is_new_session": True,
        }

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Return current state computed from elapsed time since creation."""
        state = self._sessions[session_id]

        # Handle terminated sessions
        if state.get("terminated"):
            return self._build_response(
                state,
                stage="failed",
                progress=0,
                status_enum="blocked",
                error="Session terminated by user",
            )

        elapsed = time.time() - state["created_at"]
        stage_durations: list[tuple[str, float, int, int]] = state["stage_durations"]

        cumulative = 0.0
        current_stage = "completed"
        current_progress = 100
        stage_frac = 1.0

        for name, dur, p_start, p_end in stage_durations:
            if elapsed < cumulative + dur:
                # We're in this stage
                stage_frac = (elapsed - cumulative) / dur
                current_progress = int(p_start + stage_frac * (p_end - p_start))
                current_stage = name

                # If this session will fail and we've reached the testing stage
                if state["will_fail"] and name == "testing":
                    return self._build_response(
                        state,
                        stage="failed",
                        progress=p_start,
                        status_enum="blocked",
                        error="Tests failed: existing tests broke after applying fix",
                    )
                break
            cumulative += dur
        else:
            # All stages completed
            if state["will_fail"]:
                return self._build_response(
                    state,
                    stage="failed",
                    progress=60,
                    status_enum="blocked",
                    error="Tests failed: existing tests broke after applying fix",
                )
            current_stage = "completed"
            current_progress = 100

        if current_stage == "completed":
            return self._build_response(
                state,
                stage="completed",
                progress=100,
                status_enum="finished",
            )

        return self._build_response(
            state,
            stage=current_stage,
            progress=current_progress,
            status_enum="working",
        )

    def _build_response(
        self,
        state: dict[str, Any],
        *,
        stage: str,
        progress: int,
        status_enum: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Build a mock Devin API response dict."""
        finding_id = state["finding_id"]
        category = state["category"]
        service = state["service"]

        fix_approach: str | None = None
        files_modified: list[str] = []
        tests_passed: bool | None = None
        tests_added: int = 0
        pr_url: str | None = None
        confidence: str | None = None

        # Populate fields based on stage progression
        stage_order = ["analyzing", "fixing", "testing", "creating_pr", "completed", "failed"]
        stage_idx = stage_order.index(stage) if stage in stage_order else 0

        if stage_idx >= 1 or stage == "failed":
            # Past analyzing -> have fix_approach and confidence
            fix_approach = _FIX_APPROACHES.get(
                category,
                "Apply security best practices to remediate the identified vulnerability",
            )
            confidence = self._rng.choice(["high", "medium"]) if category != "other" else "low"

        if stage_idx >= 2 or (stage == "failed"):
            # Past fixing -> have files_modified
            templates = _FILE_TEMPLATES.get(category, ["src/main/fix.java"])
            files_modified = [
                t.format(
                    service=service.replace("-service", ""),
                    cls=finding_id.replace("-", ""),
                )
                for t in templates[:2]
            ]

        if stage_idx >= 3:
            # Past testing -> have test results
            tests_passed = True
            tests_added = self._rng.randint(1, 5)

        if stage == "failed":
            tests_passed = False
            tests_added = 0

        if stage in ("creating_pr", "completed"):
            pr_number = self._rng.randint(10, 999)
            pr_url = f"https://github.com/coupang-demo/{service}/pull/{pr_number}"

        # Current step messages
        step_messages = {
            "analyzing": f"Analyzing finding {finding_id}: {category.replace('_', ' ').title()} in {service}",
            "fixing": f"Applying fix for {finding_id} — {fix_approach or 'patching vulnerability'}",
            "testing": f"Running test suite — validating fix for {finding_id}",
            "creating_pr": f"Creating pull request with fix for {finding_id}",
            "completed": "Pull request created successfully",
            "failed": "Tests failed after applying fix",
        }

        structured_output = {
            "finding_id": finding_id,
            "status": stage,
            "progress_pct": progress,
            "current_step": step_messages.get(stage, "Processing..."),
            "fix_approach": fix_approach,
            "files_modified": files_modified,
            "tests_passed": tests_passed,
            "tests_added": tests_added,
            "pr_url": pr_url,
            "error_message": error,
            "confidence": confidence,
        }

        pull_request = None
        if stage == "completed" and pr_url:
            pull_request = {"url": pr_url}

        return {
            "session_id": state["session_id"],
            "status_enum": status_enum,
            "url": f"https://app.devin.ai/sessions/{state['session_id']}",
            "title": f"Remediate {finding_id}: {category.replace('_', ' ').title()}",
            "structured_output": structured_output,
            "pull_request": pull_request,
        }

    async def list_sessions(
        self,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List sessions, optionally filtered by tags."""
        all_sessions = list(self._sessions.values())

        if tags:
            tag_set = set(tags)
            all_sessions = [
                s for s in all_sessions if tag_set.issubset(set(s.get("tags", [])))
            ]

        total = len(all_sessions)
        page = all_sessions[offset : offset + limit]

        sessions_out = []
        for s in page:
            sessions_out.append(await self.get_session(s["session_id"]))

        return {"sessions": sessions_out, "total": total}

    async def send_message(self, session_id: str, message: str) -> None:
        """No-op. Log the message for debugging."""
        logger.debug("Mock send_message to %s: %s", session_id, message[:100])

    async def terminate_session(self, session_id: str) -> None:
        """Mark the session as terminated/failed immediately."""
        if session_id in self._sessions:
            self._sessions[session_id]["terminated"] = True
            logger.info("Mock session terminated: %s", session_id)

    async def create_playbook(self, title: str, body: str) -> dict[str, Any]:
        """Store and return a fake playbook_id."""
        playbook_id = f"pb-mock-{uuid.uuid4().hex[:8]}"
        self._playbooks[playbook_id] = {
            "playbook_id": playbook_id,
            "title": title,
            "body": body,
        }
        logger.info("Mock playbook created: %s (%s)", playbook_id, title)
        return {"playbook_id": playbook_id, "title": title}

    async def list_playbooks(self) -> dict[str, Any]:
        """Return all stored mock playbooks."""
        return {"playbooks": list(self._playbooks.values())}

    async def terminate_session_best_effort(self, session_id: str) -> None:
        """Best-effort terminate — same as terminate_session for mock."""
        await self.terminate_session(session_id)

    def reset_circuit_breaker(self) -> None:
        """No-op — mock client has no circuit breaker."""
        pass

    async def close(self) -> None:
        """No-op — nothing to clean up."""
        pass

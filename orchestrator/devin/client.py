from __future__ import annotations

import asyncio
import logging
import random
import time as _time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_RETRYABLE_STATUSES = {429, 500, 502, 503}


class DevinAPIError(Exception):
    """Raised on non-2xx responses from the Devin API."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"Devin API error {status}: {message}")


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and rejecting requests."""


class CircuitBreaker:
    """Simple circuit breaker with closed/open/half-open states."""

    def __init__(self, threshold: int = 5, cooldown_seconds: int = 30) -> None:
        self._threshold = threshold
        self._cooldown = cooldown_seconds
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._state: str = "closed"  # closed | open | half_open

    @property
    def state(self) -> str:
        if self._state == "open":
            if _time.monotonic() - self._last_failure_time >= self._cooldown:
                self._state = "half_open"
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = _time.monotonic()
        if self._failure_count >= self._threshold:
            self._state = "open"
            logger.warning("Circuit breaker OPEN after %d failures", self._failure_count)

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._failure_count = 0
        self._state = "closed"

    def check(self) -> None:
        """Raise CircuitBreakerOpen if circuit is open."""
        state = self.state
        if state == "open":
            raise CircuitBreakerOpen(
                f"Circuit breaker is open (cooldown {self._cooldown}s remaining)"
            )
        # half_open: allow one probe through (don't raise)


class DevinClient:
    """Async wrapper around the Devin v1 REST API using aiohttp."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.devin.ai/v1",
        max_retries: int = 3,
        retry_jitter_max: float = 1.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_cooldown: int = 30,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._retry_jitter_max = retry_jitter_max
        self._circuit_breaker = CircuitBreaker(
            threshold=circuit_breaker_threshold,
            cooldown_seconds=circuit_breaker_cooldown,
        )
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Lazily create the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._session

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an HTTP request with retry logic, jitter, Retry-After, and circuit breaker.

        Retries on 429, 500, 502, 503 with exponential backoff + jitter.
        Respects Retry-After header (capped at 60s).
        Circuit breaker rejects requests when too many consecutive failures occur.
        """
        self._circuit_breaker.check()
        session = await self._ensure_session()
        url = f"{self._base_url}{path}"
        last_status = 0

        for attempt in range(self._max_retries + 1):
            try:
                async with session.request(method, url, **kwargs) as resp:
                    last_status = resp.status

                    if resp.status in _RETRYABLE_STATUSES and attempt < self._max_retries:
                        # Retry-After header takes precedence
                        retry_after = resp.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait = min(float(retry_after), 60.0)
                            except ValueError:
                                wait = float(2 ** attempt)
                        else:
                            wait = float(2 ** attempt)
                        # Add jitter
                        wait += random.uniform(0, self._retry_jitter_max)
                        logger.warning(
                            "Retryable error %d on %s %s, retrying in %.1fs (attempt %d/%d)",
                            resp.status, method, path, wait, attempt + 1, self._max_retries,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if resp.status >= 400:
                        body = await resp.text()
                        self._circuit_breaker.record_failure()
                        raise DevinAPIError(resp.status, body)

                    # Success
                    self._circuit_breaker.record_success()
                    if resp.status == 204 or resp.content_length == 0:
                        return {}
                    try:
                        return await resp.json()
                    except (aiohttp.ContentTypeError, Exception):
                        return {}

            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                self._circuit_breaker.record_failure()
                if attempt < self._max_retries:
                    wait = float(2 ** attempt) + random.uniform(0, self._retry_jitter_max)
                    logger.warning(
                        "Network error on %s %s: %s, retrying in %.1fs",
                        method, path, exc, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                raise DevinAPIError(0, str(exc)) from exc

        self._circuit_breaker.record_failure()
        raise DevinAPIError(last_status, f"Retryable error after {self._max_retries} retries")

    async def create_session(
        self,
        prompt: str,
        playbook_id: str | None = None,
        tags: list[str] | None = None,
        structured_output_schema: dict[str, Any] | None = None,
        max_acu_limit: int | None = None,
        idempotent: bool = True,
    ) -> dict[str, Any]:
        """POST /v1/sessions — create a new Devin session.

        Returns: {"session_id": str, "url": str, "is_new_session": bool}
        """
        body: dict[str, Any] = {"prompt": prompt}
        if playbook_id is not None:
            body["playbook_id"] = playbook_id
        if tags is not None:
            body["tags"] = tags
        if structured_output_schema is not None:
            body["structured_output_schema"] = structured_output_schema
        if max_acu_limit is not None:
            body["max_acu_limit"] = max_acu_limit
        body["idempotent"] = idempotent

        return await self._request("POST", "/sessions", json=body)

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """GET /v1/sessions/{session_id} — get full session details.

        Returns session details including status_enum, structured_output,
        and pull_request.
        """
        return await self._request("GET", f"/sessions/{session_id}")

    async def list_sessions(
        self,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Any:
        """GET /v1/sessions — list sessions with optional tag filtering.

        Returns: list or {"sessions": [...], "total": int}
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if tags:
            params["tags"] = ",".join(tags)
        return await self._request("GET", "/sessions", params=params)

    async def send_message(self, session_id: str, message: str) -> None:
        """POST /v1/sessions/{session_id}/message — send a message to a session."""
        await self._request(
            "POST", f"/sessions/{session_id}/message", json={"message": message}
        )

    async def terminate_session(self, session_id: str) -> None:
        """DELETE /v1/sessions/{session_id} — terminate a session."""
        await self._request("DELETE", f"/sessions/{session_id}")

    async def terminate_session_best_effort(self, session_id: str) -> None:
        """Terminate a session without tripping the circuit breaker.

        Used for cleanup of stale sessions where 404 (already gone) is expected
        and should not count as a failure.
        """
        try:
            await self._request("DELETE", f"/sessions/{session_id}")
        except DevinAPIError as exc:
            if exc.status == 404:
                # Already terminated — undo the circuit breaker failure
                self._circuit_breaker.record_success()
            else:
                raise

    async def create_playbook(self, title: str, body: str) -> dict[str, Any]:
        """POST /v1/playbooks — create a playbook.

        Returns: {"playbook_id": str, ...}
        """
        return await self._request(
            "POST", "/playbooks", json={"title": title, "body": body}
        )

    async def list_playbooks(self) -> Any:
        """GET /v1/playbooks — list all playbooks.

        Returns: list of playbook objects from the real API,
        or {"playbooks": [...]} from the mock client.
        """
        return await self._request("GET", "/playbooks")

    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker to closed state. Call after cleanup operations."""
        self._circuit_breaker.reset()

    async def close(self) -> None:
        """Close the underlying aiohttp session. Safe to call multiple times."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

from __future__ import annotations

from orchestrator.models import Finding, RemediationSession, SessionStatus, Wave


def create_waves(
    findings: list[Finding],
    wave_size: int = 10,
) -> list[Wave]:
    """Group priority-sorted findings into waves of up to wave_size each."""
    if not findings:
        return []

    waves: list[Wave] = []
    for i in range(0, len(findings), wave_size):
        wave_number = i // wave_size + 1
        chunk = findings[i : i + wave_size]

        sessions = [
            RemediationSession(
                finding=f,
                playbook_id="",
                status=SessionStatus.PENDING,
                wave_number=wave_number,
                attempt=1,
            )
            for f in chunk
        ]

        waves.append(
            Wave(
                wave_number=wave_number,
                sessions=sessions,
                status="pending",
            )
        )

    return waves

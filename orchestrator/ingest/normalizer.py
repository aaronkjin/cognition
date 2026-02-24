import logging

from orchestrator.models import Finding, Severity

logger = logging.getLogger(__name__)

# Severity ranking for comparison (higher = more severe)
_SEVERITY_RANK = {
    Severity.CRITICAL: 4,
    Severity.HIGH: 3,
    Severity.MEDIUM: 2,
    Severity.LOW: 1,
}


def normalize_findings(findings: list[Finding]) -> list[Finding]:
    """Deduplicate and validate findings.

    Deduplication key: (service_name, file_path, line_number, category)
    If two findings share the same dedup key, keep the one with higher severity.
    If same severity, keep the first one encountered.

    Returns deduplicated findings preserving original order (of kept items).
    """
    seen: dict[tuple[str, str, int | None, str], int] = {}
    result: list[Finding] = []

    for finding in findings:
        key = (finding.service_name, finding.file_path, finding.line_number, finding.category.value)

        if key not in seen:
            seen[key] = len(result)
            result.append(finding)
        else:
            existing_idx = seen[key]
            existing = result[existing_idx]
            if _SEVERITY_RANK[finding.severity] > _SEVERITY_RANK[existing.severity]:
                result[existing_idx] = finding
                logger.debug(
                    "Replaced %s (%s) with %s (%s) for dedup key %s",
                    existing.finding_id,
                    existing.severity.value,
                    finding.finding_id,
                    finding.severity.value,
                    key,
                )

    duplicates_removed = len(findings) - len(result)
    if duplicates_removed > 0:
        logger.info("Removed %d duplicate findings", duplicates_removed)

    return result

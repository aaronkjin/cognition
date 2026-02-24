import csv
import logging
from pathlib import Path

from orchestrator.models import Finding, FindingCategory, Severity

logger = logging.getLogger(__name__)

# Pre-compute valid enum values for fast lookup
_VALID_CATEGORIES = {e.value for e in FindingCategory}
_VALID_SEVERITIES = {e.value for e in Severity}

# Optional fields that should map "" -> None
_OPTIONAL_FIELDS = {"cwe_id", "dependency_name", "current_version", "fixed_version", "language", "line_number"}


def parse_findings_csv(file_path: str) -> list[Finding]:
    """Parse a CSV file of security findings into Finding objects.

    CSV columns match Finding model field names:
    finding_id, scanner, category, severity, title, description,
    service_name, repo_url, file_path, line_number, cwe_id,
    dependency_name, current_version, fixed_version, language

    - Empty cells for optional fields → None
    - line_number: convert to int, or None if empty/invalid
    - Rows with invalid category or severity values → skip with warning log
    - priority_score is NOT set here (that's the prioritizer's job)
    """
    findings: list[Finding] = []
    path = Path(file_path)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            finding_id = row.get("finding_id", "unknown")

            # Validate category
            raw_category = row.get("category", "")
            if raw_category not in _VALID_CATEGORIES:
                logger.warning("Skipping %s: invalid category '%s'", finding_id, raw_category)
                continue

            # Validate severity
            raw_severity = row.get("severity", "")
            if raw_severity not in _VALID_SEVERITIES:
                logger.warning("Skipping %s: invalid severity '%s'", finding_id, raw_severity)
                continue

            # Map empty strings to None for optional fields
            for field in _OPTIONAL_FIELDS:
                if row.get(field, "") == "":
                    row[field] = None

            # Convert line_number to int or None
            ln = row.get("line_number")
            if ln is not None:
                try:
                    row["line_number"] = int(ln)
                except (ValueError, TypeError):
                    row["line_number"] = None

            findings.append(
                Finding(
                    finding_id=row["finding_id"],
                    scanner=row["scanner"],
                    category=FindingCategory(raw_category),
                    severity=Severity(raw_severity),
                    title=row["title"],
                    description=row["description"],
                    service_name=row["service_name"],
                    repo_url=row["repo_url"],
                    file_path=row["file_path"],
                    line_number=row["line_number"],
                    cwe_id=row.get("cwe_id"),
                    dependency_name=row.get("dependency_name"),
                    current_version=row.get("current_version"),
                    fixed_version=row.get("fixed_version"),
                    language=row.get("language"),
                    priority_score=0.0,
                )
            )

    logger.info("Parsed %d findings from %s", len(findings), file_path)
    return findings

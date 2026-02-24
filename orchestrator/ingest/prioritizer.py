from orchestrator.models import Finding, FindingCategory, Severity

_SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.CRITICAL: 40.0,
    Severity.HIGH: 30.0,
    Severity.MEDIUM: 15.0,
    Severity.LOW: 5.0,
}

_CATEGORY_WEIGHTS: dict[FindingCategory, float] = {
    FindingCategory.SQL_INJECTION: 25.0,
    FindingCategory.HARDCODED_SECRET: 25.0,
    FindingCategory.DEPENDENCY_VULNERABILITY: 20.0,
    FindingCategory.XSS: 20.0,
    FindingCategory.PATH_TRAVERSAL: 20.0,
    FindingCategory.PII_LOGGING: 15.0,
    FindingCategory.MISSING_ENCRYPTION: 15.0,
    FindingCategory.ACCESS_LOGGING: 10.0,
    FindingCategory.OTHER: 10.0,
}

_SERVICE_WEIGHTS: dict[str, float] = {
    "payment-service": 20.0,
    "user-service": 15.0,
    "auth-service": 20.0,
    "catalog-service": 10.0,
}
_DEFAULT_SERVICE_WEIGHT: float = 10.0


def prioritize_findings(findings: list[Finding]) -> list[Finding]:
    """Score and sort findings by priority (highest first).

    priority_score = severity_weight + category_weight + service_weight
    Range: 25 (low + access_logging + default) to 85 (critical + sqli + payment-service)

    Mutates each finding's priority_score in place so all holders of these
    objects see the computed scores.  Returns a NEW sorted list (the input
    list's order is not changed).
    """
    for f in findings:
        f.priority_score = (
            _SEVERITY_WEIGHTS[f.severity]
            + _CATEGORY_WEIGHTS[f.category]
            + _SERVICE_WEIGHTS.get(f.service_name, _DEFAULT_SERVICE_WEIGHT)
        )

    return sorted(findings, key=lambda x: x.priority_score, reverse=True)

export type Severity = "critical" | "high" | "medium" | "low";

export type FindingCategory =
  | "dependency_vulnerability"
  | "sql_injection"
  | "hardcoded_secret"
  | "pii_logging"
  | "missing_encryption"
  | "access_logging"
  | "xss"
  | "path_traversal"
  | "other";

export type SessionStatus =
  | "pending"
  | "dispatched"
  | "working"
  | "blocked"
  | "success"
  | "failed"
  | "timeout";

export interface Finding {
  finding_id: string;
  scanner: string;
  category: FindingCategory;
  severity: Severity;
  title: string;
  description: string;
  service_name: string;
  repo_url: string;
  file_path: string;
  line_number: number | null;
  cwe_id: string | null;
  dependency_name: string | null;
  current_version: string | null;
  fixed_version: string | null;
  language: string | null;
  priority_score: number;
}

export interface RemediationSession {
  session_id: string | null;
  finding: Finding;
  playbook_id: string;
  status: SessionStatus;
  devin_url: string | null;
  pr_url: string | null;
  structured_output: Record<string, unknown> | null;
  wave_number: number;
  attempt: number;
  created_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  data_source: "live" | "mock";
  version: number;
  // HITL review fields
  review_status: "pending" | "approved" | "rejected" | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_reason: string | null;
}

export interface Wave {
  wave_number: number;
  sessions: RemediationSession[];
  status: string;
  success_count: number;
  failure_count: number;
}

export interface TimelineEvent {
  timestamp: string;
  event_type: string;
  message: string;
  details: Record<string, unknown>;
}

export interface BatchRun {
  run_id: string;
  started_at: string;
  waves: Wave[];
  total_findings: number;
  completed: number;
  successful: number;
  failed: number;
  prs_created: number;
  status: string;
  data_source: "live" | "mock" | "hybrid";
  events: TimelineEvent[];
}

/** Summary entry for runs/index.json */
export interface RunSummary {
  run_id: string;
  started_at: string;
  status: string;
  total_findings: number;
  csv_filename: string | null;
  data_source: "live" | "mock" | "hybrid";
}

/** Per-category evaluation metrics */
export interface CategoryEvalMetrics {
  category: FindingCategory;
  total: number;
  succeeded: number;
  failed: number;
  pass_rate: number;
  avg_duration_seconds: number | null;
  retry_count: number;
  avg_confidence: number | null;
  health: "healthy" | "degraded" | "critical" | "insufficient_data";
}

/** Overall eval summary */
export interface EvalSummary {
  run_id: string;
  total_categories: number;
  healthy_count: number;
  degraded_count: number;
  critical_count: number;
  insufficient_count: number;
  categories: CategoryEvalMetrics[];
}

/** Ops metrics */
export interface OpsMetrics {
  run_id: string;
  status: string;
  p50_duration: number | null;
  p95_duration: number | null;
  avg_duration: number | null;
  min_duration: number | null;
  max_duration: number | null;
  sessions_per_hour: number | null;
  findings_completed: number;
  findings_total: number;
  projected_completion_minutes: number | null;
  estimated_acu_used: number | null;
  estimated_acu_budget: number | null;
  acu_burn_rate_per_hour: number | null;
  current_wave: number;
  total_waves: number;
  started_at: string;
  elapsed_minutes: number;
}

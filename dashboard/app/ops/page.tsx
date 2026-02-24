"use client";

import { useOps } from "@/lib/use-status";
import { StatusBadge } from "@/components/status-badge";

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "---";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatRate(value: number | null, unit: string): string {
  if (value === null) return "Calculating...";
  return `${value.toFixed(1)} ${unit}`;
}

function formatMinutes(value: number | null): string {
  if (value === null) return "---";
  const clamped = Math.max(0, value);
  if (clamped >= 60) {
    const h = Math.floor(clamped / 60);
    const m = Math.round(clamped % 60);
    return `~${h}h ${m}m`;
  }
  return `~${Math.round(clamped)}m`;
}

function formatAcu(value: number | null): string {
  if (value === null) return "---";
  return `${value.toFixed(1)} ACU`;
}

export default function OpsPage() {
  const { data, isLoading } = useOps();

  if (isLoading) {
    return (
      <div>
        <h1 className="font-serif text-3xl font-bold mb-6">Operations</h1>
        <div className="grid grid-cols-5 gap-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="animate-pulse rounded-lg border border-border p-6"
            >
              <div className="h-3 w-20 rounded bg-muted" />
              <div className="mt-4 h-8 w-16 rounded bg-muted" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <h1 className="font-serif text-3xl font-bold mb-6">Operations</h1>
        <p className="text-muted-foreground">No operational data available</p>
      </div>
    );
  }

  const completionPct =
    data.findings_total > 0
      ? Math.round((data.findings_completed / data.findings_total) * 100)
      : 0;

  const acuPct =
    data.estimated_acu_budget && data.estimated_acu_budget > 0 && data.estimated_acu_used !== null
      ? Math.min(
          100,
          Math.round(
            (data.estimated_acu_used / data.estimated_acu_budget) * 100
          )
        )
      : 0;

  // Alert conditions
  const slowP95 = data.p95_duration !== null && data.p95_duration > 600;
  const longEta =
    data.projected_completion_minutes !== null &&
    data.projected_completion_minutes > 120;

  let acuOverburn = false;
  if (
    data.acu_burn_rate_per_hour !== null &&
    data.estimated_acu_budget !== null &&
    data.estimated_acu_used !== null &&
    data.elapsed_minutes > 0
  ) {
    const remainingBudget = data.estimated_acu_budget - data.estimated_acu_used;
    const remainingHours =
      data.projected_completion_minutes !== null && data.projected_completion_minutes > 0
        ? data.projected_completion_minutes / 60
        : null;
    if (
      remainingHours !== null &&
      remainingHours > 0.01 &&
      data.acu_burn_rate_per_hour * remainingHours > remainingBudget
    ) {
      acuOverburn = true;
    }
  }

  const hasAlerts = slowP95 || longEta || acuOverburn;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <h1 className="font-serif text-3xl font-bold">Operations</h1>
      </div>

      {/* Status Bar */}
      <div className="mb-6 flex items-center gap-4 rounded-lg border border-border p-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Run
          </span>
          <span className="font-mono text-xs text-foreground">
            {data.run_id}
          </span>
        </div>
        <StatusBadge status={data.status} />
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">Elapsed</span>
          <span className="text-xs font-medium text-foreground">
            {data.elapsed_minutes}m
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">Wave</span>
          <span className="text-xs font-medium text-foreground">
            {data.current_wave}/{data.total_waves}
          </span>
        </div>
      </div>

      {/* Alert Badges */}
      {hasAlerts && (
        <div className="mb-6 flex flex-wrap gap-2">
          {slowP95 && (
            <span className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20">
              Slow p95
            </span>
          )}
          {acuOverburn && (
            <span className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20 dark:bg-red-900/50 dark:text-red-400 dark:ring-red-500/20">
              ACU overburn
            </span>
          )}
          {longEta && (
            <span className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20">
              Long ETA
            </span>
          )}
        </div>
      )}

      {/* Duration Cards */}
      <h2 className="font-serif text-xl font-semibold mb-4">
        Session Durations
      </h2>
      <div className="grid grid-cols-5 gap-6 mb-8">
        <DurationCard label="p50 Duration" value={data.p50_duration} />
        <DurationCard label="p95 Duration" value={data.p95_duration} />
        <DurationCard label="Avg Duration" value={data.avg_duration} />
        <DurationCard label="Min Duration" value={data.min_duration} />
        <DurationCard label="Max Duration" value={data.max_duration} />
      </div>

      {/* Throughput Section */}
      <h2 className="font-serif text-xl font-semibold mb-4">Throughput</h2>
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="rounded-lg border border-border p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Sessions / Hour
          </p>
          <p className="mt-2 font-serif text-3xl font-bold text-foreground">
            {formatRate(data.sessions_per_hour, "sessions/hr")}
          </p>
        </div>
        <div className="rounded-lg border border-border p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Completion
          </p>
          <p className="mt-2 font-serif text-3xl font-bold text-foreground">
            {data.findings_completed}/{data.findings_total}
          </p>
          <div className="mt-4 border-t border-border pt-3">
            <div className="h-2 w-full rounded-full bg-muted">
              <div
                className="h-2 rounded-full bg-emerald-500 dark:bg-emerald-400 transition-all"
                style={{ width: `${completionPct}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {completionPct}% complete
            </p>
          </div>
        </div>
        <div className="rounded-lg border border-border p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Projected Remaining
          </p>
          <p className="mt-2 font-serif text-3xl font-bold text-foreground">
            {formatMinutes(data.projected_completion_minutes)}
          </p>
        </div>
      </div>

      {/* ACU Section */}
      <h2 className="font-serif text-xl font-semibold mb-4">ACU Budget</h2>
      <div className="grid grid-cols-3 gap-6">
        <div className="rounded-lg border border-border p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Estimated ACU Used
          </p>
          <p className="mt-2 font-serif text-3xl font-bold text-foreground">
            {formatAcu(data.estimated_acu_used)}
          </p>
          <div className="mt-4 border-t border-border pt-3">
            <div className="h-2 w-full rounded-full bg-muted">
              <div
                className={`h-2 rounded-full transition-all ${
                  acuPct > 80
                    ? "bg-red-500 dark:bg-red-400"
                    : "bg-emerald-500 dark:bg-emerald-400"
                }`}
                style={{ width: `${acuPct}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {acuPct}% of budget
            </p>
          </div>
        </div>
        <div className="rounded-lg border border-border p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            ACU Budget
          </p>
          <p className="mt-2 font-serif text-3xl font-bold text-foreground">
            {data.estimated_acu_budget !== null
              ? `${data.estimated_acu_budget} ACU`
              : "---"}
          </p>
        </div>
        <div className="rounded-lg border border-border p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Burn Rate
          </p>
          <p className="mt-2 font-serif text-3xl font-bold text-foreground">
            {formatRate(data.acu_burn_rate_per_hour, "ACU/hr")}
          </p>
        </div>
      </div>
    </div>
  );
}

function DurationCard({
  label,
  value,
}: {
  label: string;
  value: number | null;
}) {
  return (
    <div className="rounded-lg border border-border p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 font-serif text-2xl font-bold text-foreground">
        {formatDuration(value)}
      </p>
    </div>
  );
}

"use client";

import type { BatchRun, Severity } from "@/lib/types";

interface OverviewCardsProps {
  data: BatchRun;
}

export function OverviewCards({ data }: OverviewCardsProps) {
  const severityCounts = countSeverities(data);
  const sessionCounts = countSessionStatuses(data);
  const successRate =
    data.completed > 0
      ? Math.round((data.successful / data.completed) * 100)
      : 0;

  return (
    <div className="grid grid-cols-4 gap-6">
      {/* Total Findings */}
      <div className="rounded-lg border border-border p-6">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Total Findings
        </p>
        <p className="mt-2 font-serif text-3xl font-bold text-foreground">
          {data.total_findings}
        </p>
        <div className="mt-4 border-t border-border pt-3">
          <p className="text-xs text-muted-foreground">
            <span className="text-red-600 dark:text-red-400">Critical {severityCounts.critical}</span>
            {" \u00b7 "}
            <span className="text-orange-500 dark:text-orange-400">High {severityCounts.high}</span>
            {" \u00b7 "}
            <span className="text-yellow-600 dark:text-yellow-400">Medium {severityCounts.medium}</span>
            {" \u00b7 "}
            <span className="text-muted-foreground">Low {severityCounts.low}</span>
          </p>
        </div>
      </div>

      {/* Active Sessions */}
      <div className="rounded-lg border border-border p-6">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Active Sessions
        </p>
        <p className="mt-2 font-serif text-3xl font-bold text-foreground">
          {sessionCounts.working + sessionCounts.dispatched}
        </p>
        <div className="mt-4 border-t border-border pt-3">
          <p className="text-xs text-muted-foreground">
            Working {sessionCounts.working} &middot; Dispatched{" "}
            {sessionCounts.dispatched} &middot; Completed{" "}
            {sessionCounts.completed}
          </p>
        </div>
      </div>

      {/* PRs Created */}
      <div className="rounded-lg border border-border p-6">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          PRs Created
        </p>
        <p className="mt-2 font-serif text-3xl font-bold text-foreground">
          {data.prs_created}
        </p>
        <div className="mt-4 border-t border-border pt-3">
          <p className="text-xs text-muted-foreground">Success rate: {successRate}%</p>
        </div>
      </div>

      {/* Completion */}
      <div className="rounded-lg border border-border p-6">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Completion
        </p>
        <p className="mt-2 font-serif text-3xl font-bold text-foreground">
          {data.completed}/{data.total_findings}
        </p>
        <div className="mt-4 border-t border-border pt-3">
          <p className="text-xs text-muted-foreground">
            <span className="text-emerald-600 dark:text-emerald-400">Successful {data.successful}</span>
            {" \u00b7 "}
            <span className="text-red-600 dark:text-red-400">Failed {data.failed}</span>
          </p>
        </div>
      </div>
    </div>
  );
}

function countSeverities(data: BatchRun): Record<Severity, number> {
  const counts: Record<Severity, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  };

  for (const wave of data.waves) {
    for (const session of wave.sessions) {
      const sev = session.finding.severity;
      if (sev in counts) {
        counts[sev]++;
      }
    }
  }

  return counts;
}

function countSessionStatuses(data: BatchRun) {
  let working = 0;
  let dispatched = 0;
  let completed = 0;

  for (const wave of data.waves) {
    for (const session of wave.sessions) {
      switch (session.status) {
        case "working":
          working++;
          break;
        case "dispatched":
          dispatched++;
          break;
        case "success":
        case "failed":
        case "timeout":
          completed++;
          break;
      }
    }
  }

  return { working, dispatched, completed };
}

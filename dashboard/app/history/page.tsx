"use client";

import { useRuns } from "@/lib/use-status";
import { DataSourceBadge } from "@/components/data-source-badge";

export default function HistoryPage() {
  const { runs, isLoading } = useRuns();

  // Sort newest first
  const sorted = [...runs].sort(
    (a, b) =>
      new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
  );

  if (isLoading) {
    return (
      <div>
        <h1 className="font-serif text-3xl font-bold mb-6">Run History</h1>
        <div className="animate-pulse rounded-lg border border-border p-6">
          <div className="h-4 w-48 rounded bg-muted" />
        </div>
      </div>
    );
  }

  if (sorted.length === 0) {
    return (
      <div>
        <h1 className="font-serif text-3xl font-bold mb-6">Run History</h1>
        <p className="text-muted-foreground">No runs found</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="font-serif text-3xl font-bold mb-6">Run History</h1>
      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Run ID
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Started
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Status
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Findings
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Mode
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((run) => (
              <tr
                key={run.run_id}
                className="border-b border-border last:border-0"
              >
                <td className="px-4 py-3 font-mono text-xs text-foreground">
                  {run.run_id}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {new Date(run.started_at).toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <RunStatusBadge status={run.status} />
                </td>
                <td className="px-4 py-3 text-foreground">
                  {run.total_findings}
                </td>
                <td className="px-4 py-3">
                  <DataSourceBadge source={run.data_source} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RunStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed:
      "bg-emerald-50 text-emerald-700 ring-emerald-600/10 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20",
    running:
      "bg-amber-50 text-amber-700 ring-amber-600/10 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20",
    paused:
      "bg-red-50 text-red-700 ring-red-600/10 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20",
    interrupted:
      "bg-red-50 text-red-700 ring-red-600/10 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20",
    pending:
      "bg-muted text-muted-foreground ring-border",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
        styles[status] ?? styles.pending
      }`}
    >
      {status}
    </span>
  );
}

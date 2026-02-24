"use client";

import { useEval } from "@/lib/use-status";
import { HealthBadge } from "@/components/health-badge";
import type { CategoryEvalMetrics } from "@/lib/types";

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "---";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatConfidence(value: number | null): string {
  if (value === null) return "---";
  if (value >= 0.8) return "High";
  if (value >= 0.4) return "Medium";
  return "Low";
}

function formatPassRate(rate: number, total: number): string {
  if (total === 0) return "---";
  return `${Math.round(rate * 100)}%`;
}

function passRateColor(rate: number, total: number): string {
  if (total === 0) return "text-muted-foreground";
  if (rate >= 0.8) return "text-emerald-600 dark:text-emerald-400";
  if (rate >= 0.5) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

function formatCategory(category: string): string {
  return category
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function EvalPage() {
  const { data, isLoading } = useEval();

  if (isLoading) {
    return (
      <div>
        <h1 className="font-serif text-3xl font-bold mb-6">Evaluation</h1>
        <div className="grid grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="animate-pulse rounded-lg border border-border p-6"
            >
              <div className="h-3 w-24 rounded bg-muted" />
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
        <h1 className="font-serif text-3xl font-bold mb-6">Evaluation</h1>
        <p className="text-muted-foreground">No evaluation data available</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="font-serif text-3xl font-bold mb-6">Evaluation</h1>

      {/* Critical Alert Banner */}
      {data.critical_count > 0 && (
        <div className="mb-6 rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3">
          <p className="text-sm font-medium text-destructive">
            Warning: {data.critical_count} categor{data.critical_count === 1 ? "y" : "ies"} below 50% pass rate
          </p>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <SummaryCard
          label="Total Categories"
          value={data.total_categories}
        />
        <SummaryCard
          label="Healthy"
          value={data.healthy_count}
          subtext="Pass rate >= 80%"
          accent="text-emerald-600 dark:text-emerald-400"
        />
        <SummaryCard
          label="Degraded"
          value={data.degraded_count}
          subtext="Pass rate 50-79%"
          accent="text-amber-600 dark:text-amber-400"
        />
        <SummaryCard
          label="Critical"
          value={data.critical_count}
          subtext="Pass rate < 50%"
          accent="text-red-600 dark:text-red-400"
        />
      </div>

      {/* Category Table */}
      <h2 className="font-serif text-xl font-semibold mb-4">
        Category Breakdown
      </h2>
      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Category
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Total
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Passed
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Failed
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Pass Rate
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Avg Duration
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Retries
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Confidence
              </th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                Health
              </th>
            </tr>
          </thead>
          <tbody>
            {data.categories.map((cat: CategoryEvalMetrics) => (
              <tr
                key={cat.category}
                className="border-b border-border last:border-0"
              >
                <td className="px-4 py-3 font-medium text-foreground">
                  {formatCategory(cat.category)}
                </td>
                <td className="px-4 py-3 text-foreground">{cat.total}</td>
                <td className="px-4 py-3 text-emerald-600 dark:text-emerald-400">
                  {cat.succeeded}
                </td>
                <td className="px-4 py-3 text-red-600 dark:text-red-400">
                  {cat.failed}
                </td>
                <td className="px-4 py-3">
                  <span className={passRateColor(cat.pass_rate, cat.total)}>
                    {formatPassRate(cat.pass_rate, cat.total)}
                  </span>
                  {cat.total > 0 && cat.total < 3 && (
                    <span className="ml-1 text-xs text-muted-foreground">
                      (low sample)
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatDuration(cat.avg_duration_seconds)}
                </td>
                <td className="px-4 py-3 text-foreground">
                  {cat.retry_count}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatConfidence(cat.avg_confidence)}
                </td>
                <td className="px-4 py-3">
                  <HealthBadge health={cat.health} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  subtext,
  accent,
}: {
  label: string;
  value: number;
  subtext?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-border p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p
        className={`mt-2 font-serif text-3xl font-bold ${accent ?? "text-foreground"}`}
      >
        {value}
      </p>
      {subtext && (
        <div className="mt-4 border-t border-border pt-3">
          <p className="text-xs text-muted-foreground">{subtext}</p>
        </div>
      )}
    </div>
  );
}

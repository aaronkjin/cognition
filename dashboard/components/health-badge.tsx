interface HealthBadgeProps {
  health: "healthy" | "degraded" | "critical" | "insufficient_data";
}

const healthStyles: Record<string, string> = {
  healthy:
    "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-900/50 dark:text-emerald-400 dark:ring-emerald-500/20",
  degraded:
    "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20",
  critical:
    "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-900/50 dark:text-red-400 dark:ring-red-500/20",
  insufficient_data: "bg-muted text-muted-foreground ring-border",
};

const healthLabels: Record<string, string> = {
  healthy: "Healthy",
  degraded: "Degraded",
  critical: "Critical",
  insufficient_data: "Low Sample",
};

export function HealthBadge({ health }: HealthBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${healthStyles[health]}`}
    >
      {healthLabels[health]}
    </span>
  );
}

interface DataSourceBadgeProps {
  source: string | undefined | null;
  size?: "sm" | "md";
}

const sourceStyles: Record<string, string> = {
  live: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-900/50 dark:text-emerald-400 dark:ring-emerald-500/20",
  mock: "bg-gray-50 text-gray-600 ring-gray-500/10 dark:bg-neutral-800 dark:text-neutral-400 dark:ring-neutral-600/20",
  hybrid:
    "bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-900/50 dark:text-blue-400 dark:ring-blue-500/20",
};

const defaultStyle =
  "bg-gray-50 text-gray-600 ring-gray-500/10 dark:bg-neutral-800 dark:text-neutral-400 dark:ring-neutral-600/20";

const labels: Record<string, string> = {
  live: "Live",
  mock: "Mock",
  hybrid: "Hybrid",
};

export function DataSourceBadge({ source, size = "sm" }: DataSourceBadgeProps) {
  const key = source ?? "unknown";
  const style = sourceStyles[key] ?? defaultStyle;
  const label = labels[key] ?? "Unknown";
  const sizeClasses =
    size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ring-1 ring-inset ${style} ${sizeClasses}`}
    >
      {label}
    </span>
  );
}

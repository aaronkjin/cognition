interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

const statusStyles: Record<string, string> = {
  completed: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-900/50 dark:text-emerald-400 dark:ring-emerald-500/20",
  success: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-900/50 dark:text-emerald-400 dark:ring-emerald-500/20",
  finished: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-900/50 dark:text-emerald-400 dark:ring-emerald-500/20",
  working: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20",
  dispatched: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20",
  in_progress: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20",
  analyzing: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20",
  fixing: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20",
  testing: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20",
  creating_pr: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-900/50 dark:text-amber-400 dark:ring-amber-500/20",
  failed: "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-900/50 dark:text-red-400 dark:ring-red-500/20",
  blocked: "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-900/50 dark:text-red-400 dark:ring-red-500/20",
  timeout: "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-900/50 dark:text-red-400 dark:ring-red-500/20",
  pending: "bg-gray-50 text-gray-600 ring-gray-500/10 dark:bg-neutral-800 dark:text-neutral-400 dark:ring-neutral-600/20",
};

const defaultStyle = "bg-gray-50 text-gray-600 ring-gray-500/10 dark:bg-neutral-800 dark:text-neutral-400 dark:ring-neutral-600/20";

function formatStatus(status: string): string {
  return status
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  const style = statusStyles[status] ?? defaultStyle;
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ring-1 ring-inset ${style} ${sizeClasses}`}
    >
      {formatStatus(status)}
    </span>
  );
}

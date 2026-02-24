import type { TimelineEvent } from "@/lib/types";

interface TraceTimelineProps {
  events: TimelineEvent[];
}

function getDotColor(eventType: string): string {
  switch (eventType) {
    case "session_completed":
      return "bg-emerald-500";
    case "session_failed":
      return "bg-red-500";
    case "session_started":
      return "bg-blue-500";
    case "session_progress":
      return "bg-amber-500";
    case "session_retry":
      return "bg-orange-500";
    case "wave_started":
      return "bg-blue-400";
    case "wave_completed":
      return "bg-emerald-400";
    case "wave_gated":
      return "bg-red-400";
    default:
      return "bg-muted-foreground";
  }
}

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function TraceTimeline({ events }: TraceTimelineProps) {
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  if (sorted.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">No events recorded</p>
    );
  }

  return (
    <div className="relative pl-6">
      {/* Vertical line */}
      <div className="absolute left-[9px] top-2 bottom-2 w-px bg-border" />

      <div className="space-y-4">
        {sorted.map((event, index) => (
          <div key={`${event.timestamp}-${index}`} className="relative flex items-start gap-3">
            {/* Dot */}
            <div
              className={`absolute left-[-18px] top-1.5 h-[10px] w-[10px] rounded-full ${getDotColor(event.event_type)}`}
            />
            {/* Content */}
            <div className="flex flex-1 items-baseline justify-between gap-4">
              <div className="flex items-baseline gap-2">
                <p className="text-sm text-foreground">{event.message}</p>
                {event.event_type === "session_progress" &&
                  (event.details as Record<string, unknown> | null)?.progress_pct != null && (
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {String((event.details as Record<string, unknown>).progress_pct)}%
                    </span>
                  )}
              </div>
              <span className="shrink-0 text-xs text-muted-foreground">
                {formatTimestamp(event.timestamp)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRuns } from "@/lib/use-status";
import { StatusBadge } from "@/components/status-badge";
import { DataSourceBadge } from "@/components/data-source-badge";

interface RunSelectorProps {
  selectedRunId: string | null;
  onSelect: (runId: string | null) => void;
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return "just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

export function RunSelector({ selectedRunId, onSelect }: RunSelectorProps) {
  const { runs } = useRuns();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Sort newest first
  const sorted = [...runs].sort(
    (a, b) =>
      new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
  );

  const selectedRun = sorted.find((r) => r.run_id === selectedRunId);

  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (
      containerRef.current &&
      !containerRef.current.contains(e.target as Node)
    ) {
      setIsOpen(false);
    }
  }, []);

  useEffect(() => {
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [handleClickOutside]);

  if (sorted.length === 0) return null;

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground hover:bg-accent transition-colors"
      >
        <span className="font-mono text-xs text-muted-foreground">
          {selectedRun ? selectedRun.run_id : "Latest run"}
        </span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`transition-transform ${isOpen ? "rotate-180" : ""}`}
        >
          <polyline points="3 5 6 8 9 5" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 z-40 mt-1 w-80 rounded-lg border border-border bg-card shadow-lg overflow-hidden">
          {/* Latest option */}
          <button
            onClick={() => {
              onSelect(null);
              setIsOpen(false);
            }}
            className={`w-full px-4 py-2.5 text-left text-sm hover:bg-accent transition-colors ${
              selectedRunId === null
                ? "bg-accent/50 text-foreground"
                : "text-muted-foreground"
            }`}
          >
            Latest run (auto)
          </button>

          <div className="border-t border-border" />

          {/* Run list */}
          <div className="max-h-64 overflow-y-auto">
            {sorted.map((run) => (
              <button
                key={run.run_id}
                onClick={() => {
                  onSelect(run.run_id);
                  setIsOpen(false);
                }}
                className={`w-full px-4 py-2.5 text-left text-sm hover:bg-accent transition-colors ${
                  selectedRunId === run.run_id
                    ? "bg-accent/50"
                    : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-foreground">
                      {run.run_id}
                    </span>
                    <StatusBadge status={run.status} size="sm" />
                    <DataSourceBadge source={run.data_source} size="sm" />
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatRelativeTime(run.started_at)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {run.total_findings} findings
                  {run.csv_filename ? ` · ${run.csv_filename}` : ""}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

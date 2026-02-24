"use client";

import { useState } from "react";
import { useLatestRun, useRunStatus } from "@/lib/use-status";
import { OverviewCards } from "@/components/overview-cards";
import { SessionsTable } from "@/components/sessions-table";
import { DataSourceBadge } from "@/components/data-source-badge";
import { ROICard } from "@/components/roi-card";
import { UploadModal } from "@/components/upload-modal";
import { RunSelector } from "@/components/run-selector";
import type { RemediationSession } from "@/lib/types";

export default function DashboardPage() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  const latestRun = useLatestRun();
  const specificRun = useRunStatus(selectedRunId);
  const { data, isLoading } = selectedRunId ? specificRun : latestRun;

  if (isLoading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-serif text-3xl font-bold">Dashboard</h1>
        </div>
        {/* Skeleton cards */}
        <div className="grid grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="animate-pulse rounded-lg border border-border p-6"
            >
              <div className="h-3 w-24 rounded bg-muted" />
              <div className="mt-4 h-8 w-16 rounded bg-muted" />
              <div className="mt-6 border-t border-border pt-3">
                <div className="h-3 w-32 rounded bg-muted" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!data || !data.run_id) {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-serif text-3xl font-bold">Dashboard</h1>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground hover:bg-accent transition-colors"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="6" y1="2" x2="6" y2="10" />
              <line x1="2" y1="6" x2="10" y2="6" />
            </svg>
            <span className="font-mono text-xs">New Run</span>
          </button>
        </div>
        <p className="text-muted-foreground">
          No active run. Upload a CSV to start a remediation run.
        </p>
        <UploadModal open={showUpload} onClose={() => setShowUpload(false)} />
      </div>
    );
  }

  // Collect all sessions across all waves
  const allSessions: RemediationSession[] = data.waves.flatMap(
    (wave) => wave.sessions,
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="font-serif text-3xl font-bold">Dashboard</h1>
          <DataSourceBadge source={data.data_source} size="md" />
        </div>
        <div className="flex items-center gap-3">
          <RunSelector
            selectedRunId={selectedRunId}
            onSelect={setSelectedRunId}
          />
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground hover:bg-accent transition-colors"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="6" y1="2" x2="6" y2="10" />
              <line x1="2" y1="6" x2="10" y2="6" />
            </svg>
            <span className="font-mono text-xs">New Run</span>
          </button>
        </div>
      </div>
      <div className="grid grid-cols-5 gap-6">
        <div className="col-span-4">
          <OverviewCards data={data} />
        </div>
        <ROICard data={data} />
      </div>
      <h2 className="font-serif text-xl font-semibold mt-10 mb-4">
        Recent Sessions
      </h2>
      <SessionsTable sessions={allSessions} />
      <UploadModal open={showUpload} onClose={() => setShowUpload(false)} />
    </div>
  );
}

"use client";

import type { BatchRun } from "@/lib/types";

interface ROICardProps {
  data: BatchRun;
}

export function ROICard({ data }: ROICardProps) {
  const engineerHoursSaved = data.successful * 3;
  const costSaved = engineerHoursSaved * 80;

  return (
    <div className="rounded-lg border border-border p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Estimated ROI
      </p>
      <p className="mt-2 font-serif text-3xl font-bold text-foreground">
        ${costSaved.toLocaleString()}
      </p>
      <div className="mt-4 border-t border-border pt-3">
        <p className="text-xs text-muted-foreground">
          {engineerHoursSaved} engineer-hours saved &middot; {data.successful}{" "}
          automated fixes
        </p>
      </div>
    </div>
  );
}

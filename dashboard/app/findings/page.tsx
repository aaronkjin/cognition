"use client";

import { useLatestRun } from "@/lib/use-status";
import { FindingsTable } from "@/components/findings-table";
import type { Finding, RemediationSession } from "@/lib/types";

export default function FindingsPage() {
  const { data, isLoading } = useLatestRun();

  if (isLoading) {
    return (
      <div>
        <h1 className="font-serif text-3xl font-bold mb-6">Findings</h1>
        <p className="text-muted-foreground">Loading findings...</p>
      </div>
    );
  }

  if (!data || !data.run_id) {
    return (
      <div>
        <h1 className="font-serif text-3xl font-bold mb-6">Findings</h1>
        <p className="text-muted-foreground">No findings loaded</p>
      </div>
    );
  }

  // Extract all findings and build session map
  const findings: Finding[] = [];
  const sessionMap: Record<string, RemediationSession> = {};

  for (const wave of data.waves) {
    for (const session of wave.sessions) {
      findings.push(session.finding);
      sessionMap[session.finding.finding_id] = session;
    }
  }

  return (
    <div>
      <h1 className="font-serif text-3xl font-bold mb-6">Findings</h1>
      <FindingsTable findings={findings} sessionMap={sessionMap} />
    </div>
  );
}

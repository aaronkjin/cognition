"use client";

import Link from "next/link";
import { useLatestRun } from "@/lib/use-status";
import { StatusBadge } from "@/components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { RemediationSession } from "@/lib/types";

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return "\u2014";
  const now = Date.now();
  const then = new Date(isoString).getTime();
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

function formatDuration(
  startIso: string | null,
  endIso: string | null
): string {
  if (!startIso || !endIso) return "\u2014";
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  const diffSec = Math.floor((end - start) / 1000);

  if (diffSec < 60) return `${diffSec}s`;
  const min = Math.floor(diffSec / 60);
  const sec = diffSec % 60;
  return `${min}m ${sec}s`;
}

function truncateId(id: string | null): string {
  if (!id) return "\u2014";
  return id.length > 12 ? id.slice(0, 12) + "\u2026" : id;
}

function getAllSessions(
  data: { waves: { wave_number: number; sessions: RemediationSession[] }[] } | undefined
): RemediationSession[] {
  if (!data?.waves) return [];
  const sessions: RemediationSession[] = [];
  for (const wave of data.waves) {
    for (const session of wave.sessions) {
      sessions.push(session);
    }
  }
  return sessions;
}

export default function SessionsPage() {
  const { data, isLoading } = useLatestRun();

  const allSessions = getAllSessions(data);
  const sorted = [...allSessions].sort((a, b) => {
    if (a.wave_number !== b.wave_number) return a.wave_number - b.wave_number;
    const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
    const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
    return bTime - aTime;
  });

  return (
    <div>
      <h1 className="font-serif text-3xl font-bold mb-1">Sessions</h1>
      <p className="text-sm text-muted-foreground mb-6">
        {isLoading ? "Loading\u2026" : `${sorted.length} sessions`}
      </p>

      {sorted.length === 0 && !isLoading ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No sessions yet
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Session ID</TableHead>
              <TableHead>Finding</TableHead>
              <TableHead>Service</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Wave</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>PR</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((session) => {
              const rowId = session.session_id ?? session.finding.finding_id;
              return (
                <TableRow key={`${session.finding.finding_id}-w${session.wave_number}-a${session.attempt}`}>
                  <TableCell>
                    <Link
                      href={`/sessions/${rowId}`}
                      className="font-mono text-sm text-foreground hover:underline"
                    >
                      {truncateId(session.session_id)}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/sessions/${rowId}`}
                      className="text-foreground hover:underline"
                    >
                      {session.finding.title}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {session.finding.service_name}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={session.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {session.wave_number}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatRelativeTime(session.created_at)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDuration(session.created_at, session.completed_at)}
                  </TableCell>
                  <TableCell>
                    {session.pr_url ? (
                      <a
                        href={session.pr_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                      >
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 16 16"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M5 11l6-6" />
                          <path d="M6 5h5v5" />
                        </svg>
                      </a>
                    ) : (
                      <span className="text-muted-foreground">&mdash;</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

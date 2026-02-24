"use client";

import Link from "next/link";
import type { RemediationSession, Severity } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface SessionsTableProps {
  sessions: RemediationSession[];
}

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
  if (!startIso) return "\u2014";
  if (!endIso) return "\u2014";

  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  const diffSec = Math.floor((end - start) / 1000);

  if (diffSec < 60) return `${diffSec}s`;
  const min = Math.floor(diffSec / 60);
  const sec = diffSec % 60;
  return `${min}m ${sec}s`;
}

function getSeverityColor(severity: Severity): string {
  switch (severity) {
    case "critical":
      return "text-red-600 dark:text-red-400";
    case "high":
      return "text-orange-500 dark:text-orange-400";
    case "medium":
      return "text-yellow-600 dark:text-yellow-400";
    case "low":
      return "text-muted-foreground";
  }
}

function truncate(str: string, maxLen: number): string {
  return str.length > maxLen ? str.slice(0, maxLen) + "\u2026" : str;
}

export function SessionsTable({ sessions }: SessionsTableProps) {
  const sorted = [...sessions]
    .sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bTime - aTime;
    })
    .slice(0, 10);

  if (sorted.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        No sessions yet
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Finding</TableHead>
          <TableHead>Service</TableHead>
          <TableHead>Severity</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Started</TableHead>
          <TableHead>Duration</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((session) => (
          <TableRow key={`${session.finding.finding_id}-w${session.wave_number}-a${session.attempt}`}>
            <TableCell>
              <Link
                href={`/sessions/${session.session_id ?? session.finding.finding_id}`}
                className="text-foreground hover:underline"
              >
                {truncate(session.finding.title, 40)}
              </Link>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {session.finding.service_name}
            </TableCell>
            <TableCell>
              <span
                className={`text-sm font-medium capitalize ${getSeverityColor(session.finding.severity)}`}
              >
                {session.finding.severity}
              </span>
            </TableCell>
            <TableCell>
              <StatusBadge status={session.status} />
            </TableCell>
            <TableCell className="text-muted-foreground text-sm">
              {formatRelativeTime(session.created_at)}
            </TableCell>
            <TableCell className="text-muted-foreground text-sm">
              {formatDuration(session.created_at, session.completed_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

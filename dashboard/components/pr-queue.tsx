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

interface PrQueueProps {
  sessions: RemediationSession[];
}

const severityOrder: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

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

export function PrQueue({ sessions }: PrQueueProps) {
  const sorted = [...sessions].sort(
    (a, b) =>
      severityOrder[a.finding.severity] - severityOrder[b.finding.severity]
  );

  if (sorted.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        No pull requests yet
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
          <TableHead>Confidence</TableHead>
          <TableHead>PR</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((session) => {
          const so = session.structured_output as Record<string, unknown> | null;
          const confidence = so?.confidence as string | undefined;

          return (
            <TableRow key={`${session.finding.finding_id}-w${session.wave_number}-a${session.attempt}`}>
              <TableCell>
                <Link
                  href={`/sessions/${session.session_id ?? session.finding.finding_id}`}
                  className="text-foreground hover:underline"
                >
                  {session.finding.title}
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
                {confidence ? (
                  <StatusBadge status={confidence} />
                ) : (
                  <span className="text-sm text-muted-foreground">&mdash;</span>
                )}
              </TableCell>
              <TableCell>
                {session.pr_url && (
                  <a
                    href={session.pr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    View PR
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
                      <path d="M3.5 8.5l5-5" />
                      <path d="M4.5 3.5h4v4" />
                    </svg>
                  </a>
                )}
              </TableCell>
              <TableCell>
                <StatusBadge status={session.status} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

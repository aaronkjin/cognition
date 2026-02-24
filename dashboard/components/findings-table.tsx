"use client";

import { useState } from "react";
import type {
  Finding,
  FindingCategory,
  RemediationSession,
  Severity,
} from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface FindingsTableProps {
  findings: Finding[];
  sessionMap: Record<string, RemediationSession>;
}

const severityOptions: Severity[] = ["critical", "high", "medium", "low"];

const categoryOptions: FindingCategory[] = [
  "dependency_vulnerability",
  "sql_injection",
  "hardcoded_secret",
  "pii_logging",
  "missing_encryption",
  "access_logging",
  "xss",
  "path_traversal",
  "other",
];

function formatCategory(cat: string): string {
  return cat
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
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

export function FindingsTable({ findings, sessionMap }: FindingsTableProps) {
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const filtered = findings.filter((f) => {
    if (severityFilter !== "all" && f.severity !== severityFilter) return false;
    if (categoryFilter !== "all" && f.category !== categoryFilter) return false;
    return true;
  });

  return (
    <div>
      {/* Filters */}
      <div className="mb-4 flex gap-4">
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="all">All Severities</option>
          {severityOptions.map((sev) => (
            <option key={sev} value={sev}>
              {sev.charAt(0).toUpperCase() + sev.slice(1)}
            </option>
          ))}
        </select>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="all">All Categories</option>
          {categoryOptions.map((cat) => (
            <option key={cat} value={cat}>
              {formatCategory(cat)}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No findings match the selected filters
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Finding ID</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Service</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Priority</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((finding) => {
              const session = sessionMap[finding.finding_id];
              return (
                <TableRow key={finding.finding_id}>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {finding.finding_id}
                  </TableCell>
                  <TableCell className="text-foreground">
                    {finding.title}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {finding.service_name}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatCategory(finding.category)}
                  </TableCell>
                  <TableCell>
                    <span
                      className={`text-sm font-medium capitalize ${getSeverityColor(finding.severity)}`}
                    >
                      {finding.severity}
                    </span>
                  </TableCell>
                  <TableCell>
                    {session ? (
                      <StatusBadge status={session.status} />
                    ) : (
                      <span className="text-xs text-muted-foreground">--</span>
                    )}
                  </TableCell>
                  <TableCell className="text-foreground font-medium">
                    {finding.priority_score.toFixed(1)}
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

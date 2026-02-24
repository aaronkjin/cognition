"use client";

import { useState } from "react";
import Link from "next/link";
import { useLatestRun } from "@/lib/use-status";
import { mutate } from "swr";
import type { RemediationSession, Severity } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { DataSourceBadge } from "@/components/data-source-badge";

type ReviewFilter = "all" | "pending" | "approved" | "rejected";

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

function ReviewStatusBadge({
  status,
}: {
  status: "approved" | "rejected" | null;
}) {
  if (status === "approved") {
    return (
      <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20">
        Approved
      </span>
    );
  }
  if (status === "rejected") {
    return (
      <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/20 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20">
        Rejected
      </span>
    );
  }
  return (
    <span className="text-xs text-muted-foreground">Pending Review</span>
  );
}

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return "";
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays}d ago`;
}

export default function ReviewPage() {
  const { data, isLoading } = useLatestRun();
  const [filter, setFilter] = useState<ReviewFilter>("all");
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Collect sessions with PRs
  const sessionsWithPrs: RemediationSession[] = [];
  if (data?.waves) {
    for (const wave of data.waves) {
      for (const session of wave.sessions) {
        if (session.pr_url) {
          sessionsWithPrs.push(session);
        }
      }
    }
  }

  // Filter
  const filtered = sessionsWithPrs.filter((s) => {
    if (filter === "all") return true;
    if (filter === "pending")
      return !s.review_status || s.review_status === "pending";
    return s.review_status === filter;
  });

  const sorted = [...filtered].sort(
    (a, b) =>
      severityOrder[a.finding.severity] - severityOrder[b.finding.severity]
  );

  const handleReview = async (
    sessionId: string,
    action: "approved" | "rejected"
  ) => {
    if (!data?.run_id) return;
    setSubmitting(true);
    try {
      const res = await fetch(`/api/sessions/${sessionId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          reason: reason || undefined,
          run_id: data.run_id,
        }),
      });
      if (!res.ok) throw new Error("Review failed");
      // Refresh run data
      await mutate(`/api/runs/${data.run_id}`);
      await mutate("/api/runs");
      setReviewingId(null);
      setReason("");
    } catch (err) {
      console.error("Review failed:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const filters: { key: ReviewFilter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "pending", label: "Pending" },
    { key: "approved", label: "Approved" },
    { key: "rejected", label: "Rejected" },
  ];

  const pendingCount = sessionsWithPrs.filter(
    (s) => !s.review_status || s.review_status === "pending"
  ).length;

  return (
    <div>
      <h1 className="font-serif text-3xl font-bold mb-1">Review</h1>
      <p className="text-sm text-muted-foreground mb-6">
        {isLoading
          ? "Loading\u2026"
          : `${sessionsWithPrs.length} pull request${sessionsWithPrs.length !== 1 ? "s" : ""} \u00b7 ${pendingCount} pending review`}
      </p>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-6">
        {filters.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f.key
                ? "bg-foreground text-background"
                : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {sorted.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          {filter === "all" ? "No pull requests yet" : `No ${filter} reviews`}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">
                  Finding
                </th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">
                  Service
                </th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">
                  Severity
                </th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">
                  PR
                </th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">
                  Review Status
                </th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">
                  Reviewer
                </th>
                <th className="text-left py-3 px-2 font-medium text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((session) => {
                const sessionKey =
                  session.session_id ?? session.finding.finding_id;
                const isReviewing = reviewingId === sessionKey;

                return (
                  <tr
                    key={`${session.finding.finding_id}-w${session.wave_number}-a${session.attempt}`}
                    className="border-b border-border"
                  >
                    <td className="py-3 px-2">
                      <Link
                        href={`/sessions/${sessionKey}`}
                        className="text-foreground hover:underline"
                      >
                        {session.finding.title}
                      </Link>
                    </td>
                    <td className="py-3 px-2 text-muted-foreground">
                      {session.finding.service_name}
                    </td>
                    <td className="py-3 px-2">
                      <span
                        className={`text-sm font-medium capitalize ${getSeverityColor(session.finding.severity)}`}
                      >
                        {session.finding.severity}
                      </span>
                    </td>
                    <td className="py-3 px-2">
                      <a
                        href={session.pr_url!}
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
                    </td>
                    <td className="py-3 px-2">
                      <ReviewStatusBadge status={session.review_status === "approved" || session.review_status === "rejected" ? session.review_status : null} />
                    </td>
                    <td className="py-3 px-2">
                      {session.reviewed_by ? (
                        <div>
                          <span className="text-sm text-foreground">
                            {session.reviewed_by}
                          </span>
                          {session.reviewed_at && (
                            <span className="text-xs text-muted-foreground ml-1">
                              {formatRelativeTime(session.reviewed_at)}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">
                          &mdash;
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-2">
                      {session.review_status === "approved" ||
                      session.review_status === "rejected" ? (
                        <span className="text-xs text-muted-foreground">
                          Reviewed
                        </span>
                      ) : isReviewing ? (
                        <div className="relative min-w-[220px] rounded-md border border-border bg-background focus-within:ring-1 focus-within:ring-ring">
                          <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Reason (optional)"
                            className="w-full resize-none rounded-md bg-transparent px-2 py-1.5 pb-8 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none"
                            rows={2}
                          />
                          <div className="absolute bottom-1.5 right-1.5 flex items-center gap-1">
                            <button
                              onClick={() =>
                                handleReview(sessionKey, "approved")
                              }
                              disabled={submitting}
                              title="Approve"
                              className="rounded-full p-1 bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 hover:bg-emerald-100 transition-colors disabled:opacity-50 dark:bg-emerald-900/50 dark:text-emerald-400 dark:ring-emerald-500/20 dark:hover:bg-emerald-900/70"
                            >
                              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="2.5 6 5 8.5 9.5 3.5" />
                              </svg>
                            </button>
                            <button
                              onClick={() =>
                                handleReview(sessionKey, "rejected")
                              }
                              disabled={submitting}
                              title="Reject"
                              className="rounded-full p-1 bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20 hover:bg-red-100 transition-colors disabled:opacity-50 dark:bg-red-900/50 dark:text-red-400 dark:ring-red-500/20 dark:hover:bg-red-900/70"
                            >
                              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="3" y1="3" x2="9" y2="9" />
                                <line x1="9" y1="3" x2="3" y2="9" />
                              </svg>
                            </button>
                            <button
                              onClick={() => {
                                setReviewingId(null);
                                setReason("");
                              }}
                              title="Cancel"
                              className="ml-0.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex gap-1">
                          <button
                            onClick={() => setReviewingId(sessionKey)}
                            className="rounded-md border border-border bg-background px-2 py-1 text-xs font-medium text-foreground hover:bg-accent"
                          >
                            Review
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

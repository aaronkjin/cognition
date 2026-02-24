"use client";

import Link from "next/link";
import { use, useState } from "react";
import { useLatestRun, useServiceOverrides } from "@/lib/use-status";
import { mutate } from "swr";
import { StatusBadge } from "@/components/status-badge";
import { DataSourceBadge } from "@/components/data-source-badge";
import { TraceTimeline } from "@/components/trace-timeline";
import { Progress } from "@/components/ui/progress";
import type { RemediationSession, TimelineEvent } from "@/lib/types";

function formatDuration(
  startIso: string | null,
  endIso: string | null,
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

function formatDateTime(isoString: string | null): string {
  if (!isoString) return "\u2014";
  return new Date(isoString).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function findSession(
  data: { waves: { sessions: RemediationSession[] }[] } | undefined,
  id: string,
): RemediationSession | null {
  if (!data?.waves) return null;
  for (const wave of data.waves) {
    for (const session of wave.sessions) {
      if (session.session_id === id || session.finding.finding_id === id) {
        return session;
      }
    }
  }
  return null;
}

function filterEvents(
  events: TimelineEvent[] | undefined,
  findingId: string,
): TimelineEvent[] {
  if (!events) return [];
  return events.filter((e) => {
    const details = e.details as Record<string, unknown> | null;
    return details?.finding_id === findingId;
  });
}

function generateSyntheticEvents(session: RemediationSession): TimelineEvent[] {
  const events: TimelineEvent[] = [];
  if (session.created_at) {
    events.push({
      timestamp: session.created_at,
      event_type: "session_started",
      message: `Session ${session.finding.finding_id} started`,
      details: { finding_id: session.finding.finding_id },
    });
  }
  if (session.completed_at && session.status === "success") {
    events.push({
      timestamp: session.completed_at,
      event_type: "session_completed",
      message: `Session ${session.finding.finding_id} completed`,
      details: { finding_id: session.finding.finding_id },
    });
  }
  if (session.completed_at && session.status === "failed") {
    events.push({
      timestamp: session.completed_at,
      event_type: "session_failed",
      message: `Session ${session.finding.finding_id} failed${session.error_message ? `: ${session.error_message}` : ""}`,
      details: { finding_id: session.finding.finding_id },
    });
  }
  return events;
}

interface KeyValueRowProps {
  label: string;
  children: React.ReactNode;
}

function KeyValueRow({ label, children }: KeyValueRowProps) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground mb-0.5">{label}</dt>
      <dd className="text-sm text-foreground">{children}</dd>
    </div>
  );
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
  return null;
}

function ReviewForm({
  sessionId,
  runId,
}: {
  sessionId: string;
  runId: string;
}) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleReview = async (action: "approved" | "rejected") => {
    setSubmitting(true);
    try {
      const res = await fetch(`/api/sessions/${sessionId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          reason: reason || undefined,
          run_id: runId,
        }),
      });
      if (!res.ok) throw new Error("Review failed");
      await mutate(`/api/runs/${runId}`);
      await mutate("/api/runs");
    } catch (err) {
      console.error("Review failed:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Add a review note (optional)..."
        className="w-full resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:bg-muted/30 rounded-md px-1 py-1 transition-colors"
        rows={3}
      />
      <div className="flex items-center justify-end gap-1.5 border-t border-border pt-3 mt-1">
        <button
          onClick={() => handleReview("approved")}
          disabled={submitting}
          title="Approve"
          className="rounded-full p-1.5 bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 hover:bg-emerald-100 transition-colors disabled:opacity-50 dark:bg-emerald-900/50 dark:text-emerald-400 dark:ring-emerald-500/20 dark:hover:bg-emerald-900/70"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 14 14"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="3 7 5.5 9.5 11 4" />
          </svg>
        </button>
        <button
          onClick={() => handleReview("rejected")}
          disabled={submitting}
          title="Reject"
          className="rounded-full p-1.5 bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20 hover:bg-red-100 transition-colors disabled:opacity-50 dark:bg-red-900/50 dark:text-red-400 dark:ring-red-500/20 dark:hover:bg-red-900/70"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 14 14"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="3.5" y1="3.5" x2="10.5" y2="10.5" />
            <line x1="10.5" y1="3.5" x2="3.5" y2="10.5" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export default function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, isLoading } = useLatestRun();
  const { overrides } = useServiceOverrides();

  if (isLoading) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">
        Loading session&hellip;
      </div>
    );
  }

  const session = findSession(data, id);

  if (!session) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-muted-foreground">Session not found</p>
        <Link
          href="/sessions"
          className="mt-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          Back to Sessions
        </Link>
      </div>
    );
  }

  const so = session.structured_output as Record<string, unknown> | null;
  const soCurrentStep = so?.current_step as string | undefined;
  const soProgressPct = (so?.progress_pct as number | undefined) ?? 0;
  const soFixApproach = so?.fix_approach as string | undefined;
  const soConfidence = so?.confidence as string | undefined;
  const soTestsAdded = so?.tests_added as number | undefined;
  const soTestsPassed = so?.tests_passed as boolean | null | undefined;
  const soFilesModified = so?.files_modified as string[] | undefined;
  const soErrorMessage = so?.error_message as string | undefined;
  const matchedEvents = filterEvents(data?.events, session.finding.finding_id);
  const timelineEvents =
    matchedEvents.length > 0 ? matchedEvents : generateSyntheticEvents(session);

  const serviceOverride = overrides[session.finding.service_name] as
    | Record<string, string>
    | undefined;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link
          href="/sessions"
          className="hover:text-foreground hover:underline"
        >
          Sessions
        </Link>
        <span>/</span>
        <span className="text-foreground font-mono">
          {session.session_id ?? session.finding.finding_id}
        </span>
      </nav>

      {/* Title */}
      <h1 className="font-serif text-2xl font-bold">{session.finding.title}</h1>

      {/* Session Status Card */}
      <div className="border border-border rounded-lg p-6">
        <h2 className="font-serif text-lg font-semibold mb-4">
          Session Details
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <KeyValueRow label="Status">
            <StatusBadge status={session.status} />
          </KeyValueRow>
          <KeyValueRow label="Data Source">
            <DataSourceBadge source={session.data_source} />
          </KeyValueRow>
          <KeyValueRow label="Session ID">
            <span className="font-mono text-xs">
              {session.session_id ?? "\u2014"}
            </span>
          </KeyValueRow>
          <KeyValueRow label="Wave">{session.wave_number}</KeyValueRow>
          <KeyValueRow label="Attempt">{session.attempt}</KeyValueRow>
          <KeyValueRow label="Created">
            {formatDateTime(session.created_at)}
          </KeyValueRow>
          <KeyValueRow label="Completed">
            {formatDateTime(session.completed_at)}
          </KeyValueRow>
          <KeyValueRow label="Duration">
            {formatDuration(session.created_at, session.completed_at)}
          </KeyValueRow>
          <KeyValueRow label="Devin URL">
            {session.devin_url ? (
              <a
                href={session.devin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
              >
                Open
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
            ) : (
              "\u2014"
            )}
          </KeyValueRow>
          <KeyValueRow label="PR URL">
            {session.pr_url ? (
              <a
                href={session.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
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
            ) : (
              "\u2014"
            )}
          </KeyValueRow>
        </div>
      </div>

      {/* Review Section — only visible when session has a PR */}
      {session.pr_url && (
        <div className="border border-border rounded-lg p-6">
          <h2 className="font-serif text-lg font-semibold mb-4">Review</h2>
          {session.review_status === "approved" ? (
            <div className="flex items-center gap-2">
              <ReviewStatusBadge status="approved" />
              <span className="text-sm text-muted-foreground">
                by {session.reviewed_by} &middot;{" "}
                {formatDateTime(session.reviewed_at)}
              </span>
            </div>
          ) : session.review_status === "rejected" ? (
            <div>
              <div className="flex items-center gap-2">
                <ReviewStatusBadge status="rejected" />
                <span className="text-sm text-muted-foreground">
                  by {session.reviewed_by} &middot;{" "}
                  {formatDateTime(session.reviewed_at)}
                </span>
              </div>
              {session.review_reason && (
                <p className="mt-2 text-sm text-muted-foreground">
                  Reason: {session.review_reason}
                </p>
              )}
            </div>
          ) : (
            <ReviewForm
              sessionId={session.session_id ?? session.finding.finding_id}
              runId={data?.run_id ?? ""}
            />
          )}
        </div>
      )}

      {/* Service Configuration */}
      {serviceOverride && (
        <div className="border border-border rounded-lg p-6">
          <h2 className="font-serif text-lg font-semibold mb-4">
            Service Configuration
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <KeyValueRow label="Language">
              {serviceOverride.language ?? "---"}
            </KeyValueRow>
            <KeyValueRow label="Test Command">
              <code className="text-xs font-mono bg-muted px-1 py-0.5 rounded">
                {serviceOverride.test_command ?? "---"}
              </code>
            </KeyValueRow>
            <KeyValueRow label="Branch Prefix">
              {serviceOverride.branch_prefix ?? "---"}
            </KeyValueRow>
            <KeyValueRow label="Deployment Notes">
              {serviceOverride.deployment_notes ?? "---"}
            </KeyValueRow>
            {serviceOverride.custom_instructions && (
              <div className="col-span-2">
                <KeyValueRow label="Custom Instructions">
                  {serviceOverride.custom_instructions}
                </KeyValueRow>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Devin Progress Card */}
      {so && (
        <div className="border border-border rounded-lg p-6">
          <h2 className="font-serif text-lg font-semibold mb-4">
            Devin Progress
          </h2>
          <div className="space-y-4">
            {/* Progress bar */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm text-muted-foreground">
                  {soCurrentStep ?? "In progress"}
                </span>
                <span className="text-sm font-medium text-foreground">
                  {soProgressPct}%
                </span>
              </div>
              <Progress value={soProgressPct} />
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-2">
              <KeyValueRow label="Fix Approach">
                {soFixApproach ?? "\u2014"}
              </KeyValueRow>
              <KeyValueRow label="Confidence">
                {soConfidence ? (
                  <StatusBadge status={soConfidence} />
                ) : (
                  "\u2014"
                )}
              </KeyValueRow>
              <KeyValueRow label="Tests Added">
                {soTestsAdded != null ? String(soTestsAdded) : "\u2014"}
              </KeyValueRow>
              <KeyValueRow label="Tests Passed">
                {soTestsPassed === true ? (
                  <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 14 14"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="3 7 6 10 11 4" />
                    </svg>
                    Passed
                  </span>
                ) : soTestsPassed === false ? (
                  <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400">
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 14 14"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <line x1="3" y1="3" x2="11" y2="11" />
                      <line x1="11" y1="3" x2="3" y2="11" />
                    </svg>
                    Failed
                  </span>
                ) : (
                  <span className="text-muted-foreground">{"\u2014"}</span>
                )}
              </KeyValueRow>
              <KeyValueRow label="Files Modified">
                {soFilesModified && soFilesModified.length > 0 ? (
                  <ul className="space-y-0.5">
                    {soFilesModified.map((file) => (
                      <li key={file} className="font-mono text-xs">
                        {file}
                      </li>
                    ))}
                  </ul>
                ) : (
                  "\u2014"
                )}
              </KeyValueRow>
            </div>

            {/* Error message */}
            {soErrorMessage && (
              <div className="mt-2 rounded-md bg-red-50 dark:bg-red-900/30 p-3">
                <p className="text-sm text-red-700 dark:text-red-400">
                  {soErrorMessage}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Trace Timeline */}
      <div className="border border-border rounded-lg p-6">
        <h2 className="font-serif text-lg font-semibold mb-4">
          Event Timeline
        </h2>
        <TraceTimeline events={timelineEvents} />
      </div>
    </div>
  );
}

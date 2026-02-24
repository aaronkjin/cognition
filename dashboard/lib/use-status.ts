"use client";

import useSWR from "swr";
import type { BatchRun, RunSummary, EvalSummary, OpsMetrics } from "./types";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

/** @deprecated Use useLatestRun instead */
export function useStatus() {
  const { data, error, isLoading } = useSWR<BatchRun>("/api/status", fetcher, {
    refreshInterval: 5000,
  });

  return { data, error, isLoading };
}

/** Fetch list of all runs from /api/runs */
export function useRuns() {
  const { data, error, isLoading } = useSWR<RunSummary[]>(
    "/api/runs",
    fetcher,
    { refreshInterval: 10000 }
  );
  return { runs: data ?? [], error, isLoading };
}

/** Fetch a specific run's full state */
export function useRunStatus(runId: string | null) {
  const { data, error, isLoading } = useSWR<BatchRun>(
    runId ? `/api/runs/${runId}` : null,
    fetcher,
    { refreshInterval: 5000 }
  );
  return { data, error, isLoading };
}

/** Fetch the latest run's full state via /api/runs → /api/runs/:id */
export function useLatestRun() {
  const { runs, isLoading: runsLoading } = useRuns();

  // Pick the most recent run (index.json is append-order, last = latest)
  const latestId = runs.length > 0 ? runs[runs.length - 1].run_id : null;

  const {
    data,
    error,
    isLoading: runLoading,
  } = useRunStatus(latestId);

  return { data, error, isLoading: runsLoading || runLoading };
}

/** Fetch eval metrics from /api/eval */
export function useEval() {
  const { data, error, isLoading } = useSWR<EvalSummary>(
    "/api/eval",
    fetcher,
    { refreshInterval: 10000 }
  );
  return { data, error, isLoading };
}

/** Fetch ops metrics from /api/ops */
export function useOps() {
  const { data, error, isLoading } = useSWR<OpsMetrics>(
    "/api/ops",
    fetcher,
    { refreshInterval: 5000 }
  );
  return { data, error, isLoading };
}

/** Fetch service overrides from /api/service-overrides */
export function useServiceOverrides() {
  const { data, error, isLoading } = useSWR<Record<string, Record<string, string>>>(
    "/api/service-overrides",
    fetcher,
    { refreshInterval: 0, revalidateOnFocus: false }
  );
  return { overrides: data ?? {}, error, isLoading };
}

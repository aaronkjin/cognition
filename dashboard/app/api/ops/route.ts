import { readFile } from "fs/promises";
import { NextResponse } from "next/server";
import path from "path";

export async function GET() {
  try {
    const indexPath = path.resolve(process.cwd(), "..", "runs", "index.json");
    const indexRaw = await readFile(indexPath, "utf-8");
    const entries = JSON.parse(indexRaw);
    if (!Array.isArray(entries) || entries.length === 0) {
      return NextResponse.json({ error: "No runs found" }, { status: 404 });
    }

    const latest = entries[entries.length - 1];
    const statePath = path.resolve(
      process.cwd(),
      "..",
      "runs",
      latest.run_id,
      "state.json"
    );
    const stateRaw = await readFile(statePath, "utf-8");
    const batchRun = JSON.parse(stateRaw);

    const opsMetrics = computeOpsMetrics(batchRun);
    return NextResponse.json(opsMetrics);
  } catch {
    return NextResponse.json(
      { error: "Could not compute ops metrics" },
      { status: 500 }
    );
  }
}

interface SessionData {
  status: string;
  created_at: string | null;
  completed_at: string | null;
}

interface WaveData {
  wave_number: number;
  sessions: SessionData[];
}

interface BatchRunData {
  run_id: string;
  status: string;
  started_at: string;
  total_findings: number;
  completed: number;
  waves: WaveData[];
}

function percentile(sorted: number[], p: number): number | null {
  if (sorted.length === 0) return null;
  const idx = Math.ceil(p * sorted.length) - 1;
  return sorted[Math.max(0, Math.min(idx, sorted.length - 1))];
}

function computeOpsMetrics(batchRun: BatchRunData) {
  const allSessions = batchRun.waves.flatMap((w) => w.sessions);
  const terminalStatuses = ["success", "failed", "timeout", "blocked"];
  const completedSessions = allSessions.filter((s) =>
    terminalStatuses.includes(s.status)
  );

  const durations = completedSessions
    .filter((s) => s.created_at && s.completed_at)
    .map(
      (s) =>
        (new Date(s.completed_at!).getTime() -
          new Date(s.created_at!).getTime()) /
        1000
    )
    .sort((a, b) => a - b);

  const p50 = percentile(durations, 0.5);
  const p95 = percentile(durations, 0.95);
  const avg =
    durations.length > 0
      ? durations.reduce((a, b) => a + b, 0) / durations.length
      : null;
  const min = durations.length > 0 ? durations[0] : null;
  const max = durations.length > 0 ? durations[durations.length - 1] : null;

  const startedAt = batchRun.started_at;
  const elapsedMs = Date.now() - new Date(startedAt).getTime();
  const elapsedHours = elapsedMs / 3_600_000;
  const elapsedMinutes = elapsedMs / 60_000;
  const sessionsPerHour =
    elapsedHours > 0.01 ? completedSessions.length / elapsedHours : null;

  const remaining = batchRun.total_findings - batchRun.completed;
  let projectedMinutes: number | null = null;
  if (sessionsPerHour && sessionsPerHour > 0 && remaining > 0) {
    projectedMinutes = Math.max(0, (remaining / sessionsPerHour) * 60);
  }

  let estAcuUsed: number | null = null;
  let acuBurnRate: number | null = null;
  if (avg !== null) {
    const avgMinutes = avg / 60;
    estAcuUsed = completedSessions.length * (avgMinutes / 15);
    if (elapsedHours > 0.01) {
      acuBurnRate = estAcuUsed / elapsedHours;
    }
  }
  const acuBudget = batchRun.total_findings * 5;

  let currentWave = 0;
  for (const wave of batchRun.waves) {
    const hasActive = wave.sessions.some(
      (s) => !terminalStatuses.includes(s.status) && s.status !== "pending"
    );
    const hasCompleted = wave.sessions.some((s) =>
      terminalStatuses.includes(s.status)
    );
    if (hasActive || hasCompleted) {
      currentWave = Math.max(currentWave, wave.wave_number);
    }
  }

  return {
    run_id: batchRun.run_id,
    status: batchRun.status,
    p50_duration: p50,
    p95_duration: p95,
    avg_duration: avg,
    min_duration: min,
    max_duration: max,
    sessions_per_hour: sessionsPerHour,
    findings_completed: batchRun.completed,
    findings_total: batchRun.total_findings,
    projected_completion_minutes: projectedMinutes,
    estimated_acu_used: estAcuUsed,
    estimated_acu_budget: acuBudget,
    acu_burn_rate_per_hour: acuBurnRate,
    current_wave: currentWave,
    total_waves: batchRun.waves.length,
    started_at: batchRun.started_at,
    elapsed_minutes: Math.round(elapsedMinutes),
  };
}

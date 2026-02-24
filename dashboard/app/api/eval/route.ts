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

    const evalSummary = computeEvalMetrics(batchRun);
    return NextResponse.json(evalSummary);
  } catch {
    return NextResponse.json(
      { error: "Could not compute eval metrics" },
      { status: 500 }
    );
  }
}

interface SessionData {
  status: string;
  finding: { category: string };
  created_at: string | null;
  completed_at: string | null;
  attempt: number;
  structured_output: { confidence?: string } | null;
}

interface WaveData {
  sessions: SessionData[];
}

interface BatchRunData {
  run_id: string;
  waves: WaveData[];
}

interface CategoryMetrics {
  category: string;
  total: number;
  succeeded: number;
  failed: number;
  pass_rate: number;
  avg_duration_seconds: number | null;
  retry_count: number;
  avg_confidence: number | null;
  health: string;
}

function computeEvalMetrics(batchRun: BatchRunData) {
  const categoryMap = new Map<string, SessionData[]>();

  for (const wave of batchRun.waves) {
    for (const session of wave.sessions) {
      const cat = session.finding.category;
      if (!categoryMap.has(cat)) categoryMap.set(cat, []);
      categoryMap.get(cat)!.push(session);
    }
  }

  const categories: CategoryMetrics[] = [];
  for (const [category, sessions] of categoryMap) {
    const total = sessions.length;
    const succeeded = sessions.filter((s) => s.status === "success").length;
    const failed = sessions.filter((s) =>
      ["failed", "timeout", "blocked"].includes(s.status)
    ).length;
    const passRate = total > 0 ? succeeded / total : 0;

    const durations = sessions
      .filter((s) => s.created_at && s.completed_at)
      .map(
        (s) =>
          (new Date(s.completed_at!).getTime() -
            new Date(s.created_at!).getTime()) /
          1000
      );
    const avgDuration =
      durations.length > 0
        ? durations.reduce((a, b) => a + b, 0) / durations.length
        : null;

    const retryCount = sessions.filter((s) => s.attempt > 1).length;

    const confidenceScores = sessions
      .filter((s) => s.structured_output?.confidence)
      .map((s) => {
        const c = s.structured_output!.confidence;
        return c === "high" ? 1.0 : c === "medium" ? 0.5 : 0.25;
      });
    const avgConfidence =
      confidenceScores.length > 0
        ? confidenceScores.reduce((a, b) => a + b, 0) / confidenceScores.length
        : null;

    let health: string;
    if (total < 3) {
      health = "insufficient_data";
    } else if (passRate >= 0.8) {
      health = "healthy";
    } else if (passRate >= 0.5) {
      health = "degraded";
    } else {
      health = "critical";
    }

    categories.push({
      category,
      total,
      succeeded,
      failed,
      pass_rate: passRate,
      avg_duration_seconds: avgDuration,
      retry_count: retryCount,
      avg_confidence: avgConfidence,
      health,
    });
  }

  const healthOrder: Record<string, number> = {
    critical: 0,
    degraded: 1,
    insufficient_data: 2,
    healthy: 3,
  };
  categories.sort(
    (a, b) => (healthOrder[a.health] ?? 4) - (healthOrder[b.health] ?? 4)
  );

  return {
    run_id: batchRun.run_id,
    total_categories: categories.length,
    healthy_count: categories.filter((c) => c.health === "healthy").length,
    degraded_count: categories.filter((c) => c.health === "degraded").length,
    critical_count: categories.filter((c) => c.health === "critical").length,
    insufficient_count: categories.filter(
      (c) => c.health === "insufficient_data"
    ).length,
    categories,
  };
}

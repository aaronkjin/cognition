import { readFile, writeFile, mkdir } from "fs/promises";
import { NextRequest, NextResponse } from "next/server";
import path from "path";
import { spawn } from "child_process";
import { randomUUID } from "crypto";

const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const RUNS_DIR = path.resolve(PROJECT_ROOT, "runs");

const REQUIRED_COLUMNS = [
  "finding_id",
  "scanner",
  "category",
  "severity",
  "title",
  "description",
  "service_name",
  "repo_url",
  "file_path",
];

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_ROWS = 5000;

/**
 * GET /api/runs — List all runs from runs/index.json
 */
export async function GET() {
  try {
    const indexPath = path.join(RUNS_DIR, "index.json");
    const raw = await readFile(indexPath, "utf-8");
    const entries = JSON.parse(raw);
    return NextResponse.json(entries);
  } catch {
    // No runs directory yet — return empty array
    return NextResponse.json([]);
  }
}

/**
 * POST /api/runs — Upload CSV and spawn orchestrator run
 */
export async function POST(request: NextRequest) {
  let runId: string | null = null;
  let runDir: string | null = null;

  try {
    // Parse multipart form data
    const formData = await request.formData();
    const file = formData.get("file");
    const waveSizeRaw = formData.get("wave_size");
    const modeRaw = formData.get("mode");

    // Validate file presence
    if (!file || !(file instanceof File)) {
      return NextResponse.json(
        { error: "Missing required file field" },
        { status: 400 },
      );
    }

    // Validate file extension
    if (!file.name.toLowerCase().endsWith(".csv")) {
      return NextResponse.json(
        { error: "File must have .csv extension" },
        { status: 400 },
      );
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { error: "File exceeds maximum size of 10MB" },
        { status: 413 },
      );
    }

    // Validate wave_size
    let waveSize = 5;
    if (waveSizeRaw !== null) {
      const parsed = parseInt(String(waveSizeRaw), 10);
      if (isNaN(parsed) || parsed < 1 || parsed > 100) {
        return NextResponse.json(
          { error: "wave_size must be a positive integer between 1 and 100" },
          { status: 400 },
        );
      }
      waveSize = parsed;
    }

    // Validate mode
    const VALID_MODES = ["mock", "live", "hybrid"] as const;
    type RunMode = (typeof VALID_MODES)[number];
    let mode: RunMode = "mock";
    if (modeRaw !== null) {
      const modeStr = String(modeRaw);
      if (!VALID_MODES.includes(modeStr as RunMode)) {
        return NextResponse.json(
          { error: `mode must be one of: ${VALID_MODES.join(", ")}` },
          { status: 400 },
        );
      }
      mode = modeStr as RunMode;
    }

    // Read file content and validate CSV structure
    const csvContent = await file.text();
    const lines = csvContent.split("\n").filter((line) => line.trim().length > 0);

    if (lines.length < 2) {
      return NextResponse.json(
        { error: "CSV must contain a header row and at least one data row" },
        { status: 400 },
      );
    }

    // Validate header columns
    const headerLine = lines[0];
    const headers = headerLine.split(",").map((h) => h.trim().toLowerCase());
    const missingColumns = REQUIRED_COLUMNS.filter(
      (col) => !headers.includes(col),
    );
    if (missingColumns.length > 0) {
      return NextResponse.json(
        { error: `Missing required columns: ${missingColumns.join(", ")}` },
        { status: 400 },
      );
    }

    // Validate row count (excluding header)
    const dataRowCount = lines.length - 1;
    if (dataRowCount > MAX_ROWS) {
      return NextResponse.json(
        { error: `CSV exceeds maximum of ${MAX_ROWS} rows (found ${dataRowCount})` },
        { status: 400 },
      );
    }

    // Generate run_id and create directory
    runId = randomUUID().slice(0, 8);
    runDir = path.join(RUNS_DIR, runId);
    await mkdir(runDir, { recursive: true });

    // Save CSV
    const csvPath = path.join(runDir, "findings.csv");
    await writeFile(csvPath, csvContent, "utf-8");

    // Write bootstrap.json (starting)
    const bootstrapPath = path.join(runDir, "bootstrap.json");
    await writeFile(
      bootstrapPath,
      JSON.stringify({
        status: "starting",
        started_at: new Date().toISOString(),
        run_id: runId,
      }),
      "utf-8",
    );

    // Spawn orchestrator process
    const spawnArgs = [
      "-m",
      "orchestrator.main",
      "run",
      csvPath,
      "--wave-size",
      String(waveSize),
    ];
    if (mode === "live") {
      spawnArgs.push("--live");
    } else if (mode === "hybrid") {
      spawnArgs.push("--hybrid");
    }

    const proc = spawn("python", spawnArgs, {
      cwd: PROJECT_ROOT,
      env: { ...process.env },
      detached: true,
      stdio: "ignore",
    });

    // Write PID
    const pidPath = path.join(runDir, "pid");
    await writeFile(pidPath, String(proc.pid ?? "unknown"), "utf-8");

    proc.unref();

    // Handle spawn error
    proc.on("error", async (err) => {
      try {
        await writeFile(
          bootstrapPath,
          JSON.stringify({
            status: "failed_to_spawn",
            started_at: new Date().toISOString(),
            run_id: runId,
            error: err.message,
          }),
          "utf-8",
        );
      } catch {
        // Best-effort error recording
      }
    });

    // Update bootstrap.json (started)
    await writeFile(
      bootstrapPath,
      JSON.stringify({
        status: "started",
        started_at: new Date().toISOString(),
        run_id: runId,
        pid: proc.pid,
      }),
      "utf-8",
    );

    // Return success
    return NextResponse.json(
      { run_id: runId, status: "started" },
      { status: 201 },
    );
  } catch (err) {
    // If we already created a run directory, record the failure
    if (runId && runDir) {
      try {
        const bootstrapPath = path.join(runDir, "bootstrap.json");
        await writeFile(
          bootstrapPath,
          JSON.stringify({
            status: "failed_to_spawn",
            started_at: new Date().toISOString(),
            run_id: runId,
            error: err instanceof Error ? err.message : "Unknown error",
          }),
          "utf-8",
        );
      } catch {
        // Best-effort
      }
    }

    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 },
    );
  }
}

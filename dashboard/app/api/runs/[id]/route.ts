import { readFile } from "fs/promises";
import { NextResponse } from "next/server";
import path from "path";

/**
 * GET /api/runs/:id — Get full run state
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  // Validate run_id format (alphanumeric + hyphens only, prevent path traversal)
  if (!/^[a-zA-Z0-9-]+$/.test(id)) {
    return NextResponse.json({ error: "Invalid run ID" }, { status: 400 });
  }

  try {
    const statePath = path.resolve(
      process.cwd(),
      "..",
      "runs",
      id,
      "state.json"
    );
    const raw = await readFile(statePath, "utf-8");
    const data = JSON.parse(raw);
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Run not found" }, { status: 404 });
  }
}

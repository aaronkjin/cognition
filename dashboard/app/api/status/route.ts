import { readFile } from "fs/promises";
import { NextResponse } from "next/server";
import path from "path";

/**
 * @deprecated Use GET /api/runs/:id instead. This route exists for backward
 * compatibility only and will be removed in a future version.
 */
export async function GET() {
  try {
    const statePath = path.resolve(process.cwd(), "..", "state.json");
    const raw = await readFile(statePath, "utf-8");
    const data = JSON.parse(raw);
    return NextResponse.json(data, {
      headers: { "X-Deprecated": "true" },
    });
  } catch {
    return NextResponse.json(
      { error: "No active run found" },
      { status: 404, headers: { "X-Deprecated": "true" } },
    );
  }
}

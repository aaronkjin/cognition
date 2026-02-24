import { readFile } from "fs/promises";
import { NextResponse } from "next/server";
import path from "path";

export async function GET() {
  try {
    const overridesPath = path.resolve(process.cwd(), "..", "service_overrides.json");
    const raw = await readFile(overridesPath, "utf-8");
    const data = JSON.parse(raw);
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({});
  }
}

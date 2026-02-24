import { readFile, writeFile, rename } from "fs/promises";
import { NextRequest, NextResponse } from "next/server";
import path from "path";
import { withFileLock } from "@/lib/file-lock";

const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const RUNS_DIR = path.resolve(PROJECT_ROOT, "runs");

interface ReviewPayload {
  action: "approved" | "rejected";
  reason?: string;
  run_id: string;
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: sessionId } = await params;

  // Validate session ID format
  if (!/^[a-zA-Z0-9_-]+$/.test(sessionId)) {
    return NextResponse.json({ error: "Invalid session ID" }, { status: 400 });
  }

  // Parse body
  let body: ReviewPayload;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  // Validate action
  if (!["approved", "rejected"].includes(body.action)) {
    return NextResponse.json(
      { error: "action must be 'approved' or 'rejected'" },
      { status: 400 }
    );
  }

  // Validate run_id
  if (!body.run_id || !/^[a-zA-Z0-9-]+$/.test(body.run_id)) {
    return NextResponse.json({ error: "Invalid run_id" }, { status: 400 });
  }

  // Derive reviewer identity from auth context, NOT from body
  // In demo mode: use X-Reviewer-Name header or fallback
  const reviewerName =
    request.headers.get("x-reviewer-name") || "dashboard-user";

  const statePath = path.resolve(RUNS_DIR, body.run_id, "state.json");

  try {
    // Use file lock for concurrent write safety (D5 protocol)
    const result = await withFileLock(statePath, async () => {
      // Read current state
      const raw = await readFile(statePath, "utf-8");
      const data = JSON.parse(raw);

      // Find the session
      let found = false;
      for (const wave of data.waves) {
        for (const session of wave.sessions) {
          if (
            session.session_id === sessionId ||
            session.finding?.finding_id === sessionId
          ) {
            // Apply review
            session.review_status = body.action;
            session.reviewed_by = reviewerName;
            session.reviewed_at = new Date().toISOString();
            session.review_reason = body.reason || null;
            session.version = (session.version || 0) + 1;
            found = true;
            break;
          }
        }
        if (found) break;
      }

      if (!found) {
        return { error: "Session not found", status: 404 };
      }

      // Append audit event to timeline
      data.events = data.events || [];
      data.events.push({
        timestamp: new Date().toISOString(),
        event_type: `review_${body.action}`,
        message: `Session ${sessionId} ${body.action} by ${reviewerName}`,
        details: {
          session_id: sessionId,
          action: body.action,
          reviewer: reviewerName,
          reason: body.reason || null,
        },
      });

      // Write back atomically (temp file + rename)
      const tmpPath = statePath + ".tmp";
      await writeFile(tmpPath, JSON.stringify(data, null, 2), "utf-8");
      await rename(tmpPath, statePath);

      return { success: true, session_id: sessionId, action: body.action };
    });

    if ("error" in result) {
      return NextResponse.json(
        { error: result.error },
        { status: result.status as number }
      );
    }

    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal error" },
      { status: 500 }
    );
  }
}

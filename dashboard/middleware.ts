import { NextRequest, NextResponse } from "next/server";

// Rate limiting state (in-memory, per-process)
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 60; // requests per window
const RATE_WINDOW_MS = 60_000; // 1 minute

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only apply to API routes
  if (!pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  // 1. Optional bearer auth
  const token = process.env.DASHBOARD_API_TOKEN;
  if (token) {
    const auth = request.headers.get("authorization");
    if (auth !== `Bearer ${token}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
  }

  // 2. Rate limiting (per IP)
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    request.headers.get("x-real-ip") ||
    "unknown";
  const now = Date.now();
  const entry = rateLimitMap.get(ip);

  if (entry && entry.resetAt > now) {
    if (entry.count >= RATE_LIMIT) {
      return NextResponse.json(
        { error: "Rate limit exceeded" },
        {
          status: 429,
          headers: {
            "Retry-After": String(Math.ceil((entry.resetAt - now) / 1000)),
          },
        },
      );
    }
    entry.count++;
  } else {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS });
  }

  // 3. Mutation route protection (POST/PUT/DELETE)
  if (["POST", "PUT", "DELETE"].includes(request.method)) {
    // Content-Type check (multipart/form-data for uploads, application/json for others)
    const contentType = request.headers.get("content-type") || "";
    if (
      !contentType.includes("multipart/form-data") &&
      !contentType.includes("application/json")
    ) {
      return NextResponse.json(
        { error: "Invalid Content-Type" },
        { status: 415 },
      );
    }

    // Origin check for browser requests
    const origin = request.headers.get("origin");
    if (origin) {
      const appOrigin = process.env.APP_ORIGIN || "http://localhost:3000";
      if (!origin.startsWith(appOrigin)) {
        return NextResponse.json(
          { error: "Cross-origin request denied" },
          { status: 403 },
        );
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: "/api/:path*",
};

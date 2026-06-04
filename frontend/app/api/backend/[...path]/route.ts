import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 120; // seconds (overrides default ~30s timeout)
export const dynamic = "force-dynamic";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

async function forward(req: NextRequest, params: { path: string[] }) {
  const upstreamPath = "/" + params.path.join("/");
  const search = req.nextUrl.search || "";
  const url = `${BACKEND}${upstreamPath}${search}`;

  const headers = new Headers();
  req.headers.forEach((v, k) => {
    if (k.startsWith("host") || k === "connection") return;
    headers.set(k, v);
  });

  const init: RequestInit = {
    method: req.method,
    headers,
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  const upstream = await fetch(url, init);
  const body = await upstream.arrayBuffer();
  return new NextResponse(body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: {
      "content-type": upstream.headers.get("content-type") || "application/json",
    },
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  return forward(req, await ctx.params);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return forward(req, await ctx.params);
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return forward(req, await ctx.params);
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return forward(req, await ctx.params);
}
export async function DELETE(req: NextRequest, ctx: Ctx) {
  return forward(req, await ctx.params);
}

import { BACKEND_URL } from "@/lib/server";

// Browser requests reach the Flask API through here, so it never needs to be public
// and the frontend never needs CORS.
const ALLOWED = new Set(["news", "search", "summarize", "ask", "compare", "briefing", "health"]);
const PASS_THROUGH_HEADERS = ["retry-after", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"];
const MAX_BODY = 10_000;

function failure(status, code, message) {
  return Response.json({ error: { code, message } }, { status, headers: { "cache-control": "no-store" } });
}

async function proxy(request, { params }) {
  const { path } = await params;
  if (path.length !== 1 || !ALLOWED.has(path[0])) return failure(404, "not_found", "Not found.");

  const target = new URL(`/api/${path[0]}`, BACKEND_URL);
  target.search = new URL(request.url).search;

  const headers = { accept: "application/json" };
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) headers["x-forwarded-for"] = forwardedFor;

  let body;
  if (request.method === "POST") {
    body = await request.text();
    if (body.length > MAX_BODY) return failure(413, "too_large", "Request is too large.");
    headers["content-type"] = "application/json";
  }

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(90_000),
    });
    const responseHeaders = new Headers({
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    });
    for (const name of PASS_THROUGH_HEADERS) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch (error) {
    if (error?.name === "TimeoutError") return failure(504, "timeout", "That took too long. Please try again.");
    return failure(502, "backend_unreachable", "We couldn't reach the BlitzFeed news service.");
  }
}

export { proxy as GET, proxy as POST };

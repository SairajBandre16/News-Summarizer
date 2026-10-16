import { cookies, headers } from "next/headers";
import { EDITIONS, EDITION_COOKIE } from "./constants";

export const BACKEND_URL = (process.env.BACKEND_URL || "http://127.0.0.1:8080").replace(/\/$/, "");

const UNREACHABLE = {
  code: "backend_unreachable",
  message: "We couldn't reach the BlitzFeed news service. Please try again in a moment.",
};

export async function getEdition() {
  const value = (await cookies()).get(EDITION_COOKIE)?.value;
  if (EDITIONS.some((e) => e.id === value)) return value;
  return process.env.DEFAULT_EDITION || "us";
}

/** Call the Flask API from the server. Resolves to { data } or { error }, never throws. */
export async function callBackend(path, { params, method = "GET", body, timeout = 20000 } = {}) {
  const url = new URL(`/api/${path}`, BACKEND_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }

  const requestHeaders = { accept: "application/json" };
  // Pass the visitor's address along so per-visitor rate limits keep working.
  const forwardedFor = (await headers()).get("x-forwarded-for");
  if (forwardedFor) requestHeaders["x-forwarded-for"] = forwardedFor;
  if (body) requestHeaders["content-type"] = "application/json";

  try {
    const response = await fetch(url, {
      method,
      headers: requestHeaders,
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(timeout),
    });
    const json = await response.json().catch(() => null);
    if (!response.ok) {
      return { error: json?.error ?? { code: "unavailable", message: "The news service returned an error." } };
    }
    return { data: json };
  } catch {
    return { error: UNREACHABLE };
  }
}

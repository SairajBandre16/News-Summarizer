import { iconResponse } from "@/lib/brand-image";

const SIZES = new Set([192, 512]);

export async function GET(_request, { params }) {
  const size = Number((await params).size);
  if (!SIZES.has(size)) return new Response("Not found", { status: 404 });
  const response = iconResponse(size);
  response.headers.set("cache-control", "public, max-age=604800, immutable");
  return response;
}

"use client";

import { useRef, useState } from "react";
import { PAGE_SIZE } from "@/lib/constants";
import ArticleGrid from "./ArticleGrid";

export default function LoadMore({ endpoint, params, offset: initialOffset, hasMore: initialHasMore, renderedIds = [] }) {
  // IDs already on the page (server-rendered or appended), so a shifting feed never shows a story twice.
  const seen = useRef(new Set(renderedIds));
  const [articles, setArticles] = useState([]);
  const [offset, setOffset] = useState(initialOffset);
  const [hasMore, setHasMore] = useState(initialHasMore);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  async function load() {
    setStatus("loading");
    try {
      const query = new URLSearchParams({ ...params, offset: String(offset), limit: String(PAGE_SIZE) });
      const response = await fetch(`/api/${endpoint}?${query}`);
      const body = await response.json();
      if (!response.ok) throw new Error(body?.error?.message);
      const fresh = body.articles.filter((a) => !seen.current.has(a.id));
      fresh.forEach((a) => seen.current.add(a.id));
      setArticles((previous) => [...previous, ...fresh]);
      setOffset(offset + body.articles.length);
      setHasMore(body.hasMore);
      setStatus("idle");
    } catch (err) {
      setError(err.message || "We couldn't load more stories. Please try again.");
      setStatus("error");
    }
  }

  return (
    <>
      {articles.length > 0 && (
        <div className="mt-12">
          <ArticleGrid articles={articles} />
        </div>
      )}
      <div className="mt-14 flex flex-col items-center gap-3">
        {hasMore ? (
          <button type="button" onClick={load} disabled={status === "loading"} className="btn-secondary min-w-48">
            {status === "loading" ? "Loading stories…" : "Load more stories"}
          </button>
        ) : (
          <p className="font-serif text-lg italic text-muted">You&apos;re all caught up.</p>
        )}
        {status === "error" && (
          <p role="alert" className="text-sm text-negative">
            {error}
          </p>
        )}
      </div>
    </>
  );
}

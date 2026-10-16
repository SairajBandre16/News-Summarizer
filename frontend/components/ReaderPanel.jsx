"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUpRightIcon, SparklesIcon } from "@heroicons/react/20/solid";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { briefToSpeech, briefUrl, timeAgo } from "@/lib/format";
import { ListenButton, SaveButton, ShareButton } from "./ArticleActions";
import { useReader } from "./ReaderContext";
import { SummarySkeleton } from "./Skeletons";
import { AskStory, Coverage } from "./StoryTools";
import SummaryView from "./SummaryView";
import Thumbnail from "./Thumbnail";

async function requestSummary(article, signal) {
  let response;
  try {
    response = await fetch("/api/summarize", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url: article.url, sig: article.sig }),
      signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new Error("Check your connection and try again.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error?.message || "We couldn't summarize this story.");
  return body;
}

export default function ReaderPanel() {
  const { article, close } = useReader();
  const dialogRef = useRef(null);
  const [results, setResults] = useState({});
  // Keep showing the last story while the panel animates closed.
  const [shown, setShown] = useState(null);
  if (article && article !== shown) setShown(article);

  const result = shown ? results[shown.id] : undefined;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (article && !dialog.open) dialog.showModal();
    if (!article && dialog.open) dialog.close();
  }, [article]);

  useEffect(() => {
    if (!article || results[article.id]) return;
    const controller = new AbortController();
    requestSummary(article, controller.signal).then(
      (data) => setResults((r) => ({ ...r, [article.id]: { data } })),
      (error) => {
        if (!controller.signal.aborted) setResults((r) => ({ ...r, [article.id]: { error: error.message } }));
      },
    );
    return () => controller.abort();
  }, [article, results]);

  function retry() {
    setResults((r) => {
      const next = { ...r };
      delete next[shown.id];
      return next;
    });
  }

  return (
    <dialog
      ref={dialogRef}
      className="reader"
      aria-labelledby="reader-title"
      onClose={close}
      onClick={(event) => {
        if (event.target === event.currentTarget) dialogRef.current?.close();
      }}
    >
      {shown && (
        <div
          className="flex h-full flex-col"
          onClick={(event) => {
            // Topic links navigate inside the app; close the panel when they do.
            if (event.target.closest?.("a[href^='/']")) dialogRef.current?.close();
          }}
        >
          <div className="flex items-center gap-1 border-b border-line px-4 py-2.5 sm:px-6">
            <span className="mr-auto inline-flex items-center gap-2 text-sm font-semibold">
              <SparklesIcon className="size-4 text-accent-ink" />
              Brief
            </span>
            <SaveButton article={shown} />
            <ShareButton title={shown.title} getUrl={() => briefUrl(window.location.origin, shown)} />
            <button type="button" className="icon-btn" aria-label="Close" onClick={() => dialogRef.current?.close()}>
              <XMarkIcon className="size-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto overscroll-contain px-5 pb-10 pt-6 sm:px-8">
            <p className="flex items-center gap-1.5 text-xs text-muted">
              <span className="font-semibold text-fg/80">{shown.source}</span>
              {shown.publishedAt && (
                <>
                  <span aria-hidden="true">·</span>
                  <time dateTime={shown.publishedAt} className="tabular-nums">
                    {timeAgo(shown.publishedAt)}
                  </time>
                </>
              )}
            </p>
            <h2 id="reader-title" className="mt-2 font-serif text-[1.85rem] font-semibold leading-[1.12] tracking-[-0.02em]">
              {shown.title}
            </h2>
            {shown.image && (
              <Thumbnail key={shown.id} src={shown.image} alt="" source={shown.source} className="mt-5 aspect-[2.2/1] w-full rounded-xl" />
            )}

            <div className="mt-8" aria-live="polite" aria-busy={!result}>
              {!result && (
                <>
                  <p className="mb-6 flex items-center gap-2.5 text-sm text-muted">
                    <span className="relative flex size-2">
                      <span className="absolute inline-flex size-full animate-ping rounded-full bg-accent opacity-75" />
                      <span className="relative inline-flex size-2 rounded-full bg-accent" />
                    </span>
                    Reading the article and writing your brief…
                  </p>
                  <SummarySkeleton />
                </>
              )}
              {result?.error && (
                <div className="rounded-xl bg-surface-2/70 p-5">
                  <p className="font-semibold">We couldn&apos;t brief this story</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{result.error}</p>
                  {shown.description && (
                    <>
                      <p className="eyebrow mt-5">What the publisher says</p>
                      <p className="mt-1 text-[15px] leading-relaxed">{shown.description}</p>
                    </>
                  )}
                  <button type="button" onClick={retry} className="btn-secondary mt-5">
                    Try again
                  </button>
                </div>
              )}
              {result?.data && <SummaryView data={result.data} />}
            </div>

            {result && (
              <div className="mt-10 space-y-10">
                {result.data && <AskStory key={`ask-${shown.id}`} article={shown} />}
                <Coverage key={`coverage-${shown.id}`} article={shown} />
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 border-t border-line px-4 py-3 sm:px-6">
            {article && result?.data && (
              <ListenButton key={shown.id} getText={() => briefToSpeech(shown.title, result.data.summary)} />
            )}
            <a href={shown.url} target="_blank" rel="noopener noreferrer" className="btn-primary flex-1">
              Read the full story
              <ArrowUpRightIcon className="size-4" />
            </a>
          </div>
        </div>
      )}
    </dialog>
  );
}

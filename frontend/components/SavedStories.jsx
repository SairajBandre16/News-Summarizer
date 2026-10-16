"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookmarkIcon } from "@heroicons/react/24/outline";
import { useMounted, useSaved } from "@/lib/hooks";
import ArticleGrid from "./ArticleGrid";
import { GridSkeleton } from "./Skeletons";

export default function SavedStories() {
  const mounted = useMounted();
  const { saved, clear } = useSaved();
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (!confirming) return;
    const timer = setTimeout(() => setConfirming(false), 3000);
    return () => clearTimeout(timer);
  }, [confirming]);

  if (!mounted) {
    return (
      <div className="mt-10">
        <GridSkeleton count={3} />
      </div>
    );
  }

  if (!saved.length) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center py-20 text-center">
        <span className="grid size-12 place-items-center rounded-2xl bg-surface-2 text-muted">
          <BookmarkIcon className="size-6" />
        </span>
        <h2 className="mt-5 font-serif text-2xl font-semibold tracking-tight">Nothing saved yet</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Tap the bookmark on any story to keep it here for later. You can brief and listen to saved stories anytime.
        </p>
        <Link href="/" className="btn-primary mt-6">
          Browse today&apos;s stories
        </Link>
      </div>
    );
  }

  return (
    <div className="mt-8">
      <div className="mb-8 flex items-center justify-between">
        <p className="text-sm text-muted">{saved.length === 1 ? "1 story" : `${saved.length} stories`}</p>
        <button
          type="button"
          className={`btn-ghost ${confirming ? "text-negative" : ""}`}
          onClick={() => {
            if (confirming) {
              clear();
              setConfirming(false);
            } else {
              setConfirming(true);
            }
          }}
        >
          {confirming ? "Tap again to clear all" : "Clear all"}
        </button>
      </div>
      <ArticleGrid articles={saved} />
    </div>
  );
}

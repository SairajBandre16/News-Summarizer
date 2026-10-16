"use client";

import Link from "next/link";
import { BookmarkIcon } from "@heroicons/react/24/outline";
import { useSaved } from "@/lib/hooks";

export default function SavedLink() {
  const { saved } = useSaved();
  const count = saved.length;

  return (
    <Link href="/saved" className="icon-btn relative" aria-label={count ? `Saved stories (${count})` : "Saved stories"}>
      <BookmarkIcon className="size-5" />
      {count > 0 && (
        <span className="absolute right-0.5 top-0.5 min-w-4 rounded-full bg-accent px-1 text-center text-[10px] font-bold leading-4 text-on-accent tabular-nums">
          {count > 99 ? "99+" : count}
        </span>
      )}
    </Link>
  );
}

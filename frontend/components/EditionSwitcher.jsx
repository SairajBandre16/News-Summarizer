"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { EDITIONS, EDITION_COOKIE } from "@/lib/constants";

function rememberEdition(id) {
  document.cookie = `${EDITION_COOKIE}=${id}; path=/; max-age=31536000; samesite=lax`;
}

export default function EditionSwitcher({ current }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function choose(id) {
    if (id === current) return;
    rememberEdition(id);
    startTransition(() => router.refresh());
  }

  return (
    <div
      role="group"
      aria-label="News edition"
      className={`flex rounded-full p-0.5 text-xs font-semibold ring-1 ring-line transition-opacity ${pending ? "opacity-50" : ""}`}
    >
      {EDITIONS.map((edition) => {
        const active = edition.id === current;
        return (
          <button
            key={edition.id}
            type="button"
            aria-pressed={active}
            title={`${edition.label} edition`}
            onClick={() => choose(edition.id)}
            className={`rounded-full px-2.5 py-1 transition ${active ? "bg-fg text-bg" : "text-muted hover:text-fg"}`}
          >
            <span className="sr-only">{edition.label}</span>
            <span aria-hidden="true">{edition.short}</span>
          </button>
        );
      })}
    </div>
  );
}

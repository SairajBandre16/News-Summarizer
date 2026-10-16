"use client";

import { SparklesIcon } from "@heroicons/react/20/solid";
import { timeAgo } from "@/lib/format";
import { ListenButton } from "./ArticleActions";
import { useReader } from "./ReaderContext";

const ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth"];

export default function BriefingCard({ briefing }) {
  const { open } = useReader();
  const isAI = briefing.mode === "ai";

  const speech = () =>
    [
      isAI ? "Here's your BlitzFeed briefing." : "Here are today's top headlines.",
      briefing.intro,
      ...briefing.items.flatMap((item, i) => [`${ORDINALS[i]}.`, `${item.headline}.`, item.summary]),
    ]
      .filter(Boolean)
      .join(" ");

  return (
    <section aria-labelledby="briefing-title" className="relative h-full overflow-hidden rounded-2xl bg-surface p-6 ring-1 ring-line sm:p-7">
      <div aria-hidden="true" className="pointer-events-none absolute -right-20 -top-20 size-64 rounded-full bg-accent/15 blur-3xl" />
      <div className="relative flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow flex items-center gap-1.5">
            <SparklesIcon className="size-4 text-accent-ink" />
            {isAI ? "AI briefing" : "At a glance"}
          </p>
          <h2 id="briefing-title" className="mt-1 font-serif text-[1.65rem] font-semibold tracking-[-0.02em]">
            Today in 60 seconds
          </h2>
        </div>
        <ListenButton getText={speech} className="shrink-0" />
      </div>

      {briefing.intro && <p className="relative mt-4 font-serif text-lg italic leading-snug text-fg/85">{briefing.intro}</p>}

      <ol className="relative mt-6 space-y-5">
        {briefing.items.map((item, i) => (
          <li key={item.article.id} className="grid grid-cols-[1.75rem_1fr] gap-x-2">
            <span className="font-serif text-xl font-semibold leading-tight text-accent-ink tabular-nums">{i + 1}</span>
            <div>
              {item.article.summarizable ? (
                <button
                  type="button"
                  onClick={() => open(item.article)}
                  className="text-left font-semibold leading-snug transition-colors hover:text-accent-ink"
                >
                  {item.headline}
                </button>
              ) : (
                <a
                  href={item.article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold leading-snug transition-colors hover:text-accent-ink"
                >
                  {item.headline}
                </a>
              )}
              {item.summary && <p className="mt-1 text-sm leading-relaxed text-muted">{item.summary}</p>}
            </div>
          </li>
        ))}
      </ol>

      <p className="relative mt-7 text-xs text-muted">
        {isAI ? "Written by AI from the top headlines" : "The top headlines right now"}, updated{" "}
        <time dateTime={briefing.generatedAt} suppressHydrationWarning>
          {timeAgo(briefing.generatedAt).toLowerCase()}
        </time>
      </p>
    </section>
  );
}

"use client";

import { ArrowUpRightIcon, SparklesIcon } from "@heroicons/react/20/solid";
import { timeAgo } from "@/lib/format";
import { SaveButton } from "./ArticleActions";
import { useReader } from "./ReaderContext";
import Thumbnail from "./Thumbnail";

function Meta({ article, className = "" }) {
  return (
    <p className={`flex items-center gap-1.5 text-xs text-muted ${className}`}>
      <span className="truncate font-semibold text-fg/80">{article.source}</span>
      {article.publishedAt && (
        <>
          <span aria-hidden="true">·</span>
          <time dateTime={article.publishedAt} suppressHydrationWarning className="shrink-0 tabular-nums">
            {timeAgo(article.publishedAt)}
          </time>
        </>
      )}
      {article.related?.length > 0 && (
        <>
          <span aria-hidden="true">·</span>
          <span
            className="shrink-0 font-semibold text-accent-ink"
            title={`Also covered by ${article.related.map((r) => r.source).join(", ")}`}
          >
            {article.related.length + 1} outlets
          </span>
        </>
      )}
    </p>
  );
}

/** The headline doubles as a stretched link covering the whole card. */
function Headline({ article, as: Tag = "h3", className }) {
  const { open } = useReader();
  const stretch = "text-left after:absolute after:inset-0 after:content-['']";
  return (
    <Tag className={className}>
      {article.summarizable ? (
        <button type="button" onClick={() => open(article)} className={stretch}>
          {article.title}
        </button>
      ) : (
        <a href={article.url} target="_blank" rel="noopener noreferrer" className={stretch}>
          {article.title}
        </a>
      )}
    </Tag>
  );
}

function Actions({ article }) {
  const { open } = useReader();
  return (
    <div className="relative z-10 mt-auto flex items-center justify-between gap-2 pt-3">
      {article.summarizable ? (
        <button
          type="button"
          onClick={() => open(article)}
          className="inline-flex items-center gap-1.5 rounded-full py-1 text-xs font-semibold text-accent-ink transition hover:gap-2"
        >
          <SparklesIcon className="size-4" />
          Brief me
        </button>
      ) : (
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 py-1 text-xs font-semibold text-muted transition hover:text-fg"
        >
          Read at {article.source}
          <ArrowUpRightIcon className="size-3.5" />
        </a>
      )}
      <SaveButton article={article} className="-mr-2" />
    </div>
  );
}

const shell = "group relative flex animate-rise flex-col";
const hoverTitle = "transition-colors group-hover:text-accent-ink";

export default function ArticleCard({ article, variant = "standard", index = 0, priority = false }) {
  const style = { animationDelay: `${Math.min(index, 10) * 45}ms` };

  if (variant === "lead") {
    return (
      <article className={shell} style={style}>
        <div className="overflow-hidden rounded-2xl">
          <Thumbnail
            src={article.image}
            alt=""
            source={article.source}
            priority={priority}
            className="aspect-[16/10] w-full transition duration-700 ease-out group-hover:scale-[1.02]"
          />
        </div>
        <Meta article={article} className="mt-5" />
        <Headline
          article={article}
          as="h2"
          className={`mt-2 font-serif text-[2rem] font-semibold leading-[1.08] tracking-[-0.02em] sm:text-[2.6rem] ${hoverTitle}`}
        />
        {article.description && (
          <p className="mt-3 line-clamp-3 max-w-[62ch] text-base leading-relaxed text-muted sm:text-lg">{article.description}</p>
        )}
        <Actions article={article} />
      </article>
    );
  }

  if (variant === "compact") {
    return (
      <article className={`${shell} flex-row gap-4 border-t border-line pt-5 first:border-t-0 first:pt-0`} style={style}>
        <div className="flex min-w-0 flex-1 flex-col">
          <Meta article={article} />
          <Headline
            article={article}
            className={`mt-1.5 line-clamp-3 font-serif text-lg font-semibold leading-snug tracking-[-0.01em] ${hoverTitle}`}
          />
          <Actions article={article} />
        </div>
        <Thumbnail src={article.image} alt="" source={article.source} compact className="size-24 shrink-0 rounded-xl" />
      </article>
    );
  }

  return (
    <article className={shell} style={style}>
      <div className="overflow-hidden rounded-xl">
        <Thumbnail
          src={article.image}
          alt=""
          source={article.source}
          className="aspect-[3/2] w-full transition duration-700 ease-out group-hover:scale-[1.03]"
        />
      </div>
      <Meta article={article} className="mt-4" />
      <Headline
        article={article}
        className={`mt-1.5 font-serif text-xl font-semibold leading-snug tracking-[-0.01em] ${hoverTitle}`}
      />
      {article.description && <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-muted">{article.description}</p>}
      <Actions article={article} />
    </article>
  );
}

import Link from "next/link";
import { SparklesIcon } from "@heroicons/react/20/solid";

const SENTIMENT = {
  positive: { label: "Positive news", dot: "bg-positive" },
  negative: { label: "Negative news", dot: "bg-negative" },
  mixed: { label: "Mixed news", dot: "bg-mixed" },
  neutral: { label: "Neutral tone", dot: "bg-muted" },
};

export function ModeBadge({ mode }) {
  const ai = mode === "ai";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold ${
        ai ? "bg-accent/15 text-accent-ink" : "bg-surface-2 text-fg/80"
      }`}
    >
      {ai && <SparklesIcon className="size-3.5" />}
      {ai ? "AI brief" : "Quick summary"}
    </span>
  );
}

export default function SummaryView({ data }) {
  const { summary } = data;
  const briefSeconds = Math.max(10, Math.round(((data.summaryWordCount / 230) * 60) / 5) * 5);
  const minutesSaved = data.readingMinutes - Math.ceil(briefSeconds / 60);
  const sentiment = SENTIMENT[summary.sentiment];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-muted">
        <ModeBadge mode={data.mode} />
        <span className="tabular-nums">
          {data.readingMinutes}-min story, {briefSeconds}-second brief
        </span>
        {minutesSaved >= 1 && <span className="font-semibold text-fg/80">Saves you about {minutesSaved} min</span>}
      </div>

      <section>
        <h3 className="eyebrow">The short version</h3>
        <p className="mt-2 font-serif text-[1.4rem] leading-snug tracking-[-0.01em]">{summary.tldr}</p>
      </section>

      {summary.keyPoints.length > 0 && (
        <section>
          <h3 className="eyebrow">Key points</h3>
          <ol className="mt-3 space-y-3.5">
            {summary.keyPoints.map((point, index) => (
              <li key={index} className="grid grid-cols-[1.5rem_1fr] gap-2 text-[15px] leading-relaxed">
                <span className="font-serif text-lg font-semibold leading-snug text-accent-ink tabular-nums">{index + 1}</span>
                <span>{point}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {summary.whyItMatters && (
        <section className="rounded-r-xl border-l-2 border-accent bg-surface-2/60 px-4 py-3.5">
          <h3 className="eyebrow">Why it matters</h3>
          <p className="mt-1.5 text-[15px] leading-relaxed">{summary.whyItMatters}</p>
        </section>
      )}

      {(sentiment || summary.topics?.length > 0) && (
        <div className="flex flex-wrap items-center gap-2">
          {sentiment && (
            <span className="mr-1 inline-flex items-center gap-1.5 text-xs font-medium text-fg/80">
              <span className={`size-2 rounded-full ${sentiment.dot}`} />
              {sentiment.label}
            </span>
          )}
          {summary.topics?.map((topic) => (
            <Link key={topic} href={`/search?q=${encodeURIComponent(topic)}`} className="tag">
              {topic}
            </Link>
          ))}
        </div>
      )}

      <div className="space-y-1.5 text-xs leading-relaxed text-muted">
        {data.notice && <p>{data.notice}</p>}
        {data.truncated && <p>This is a very long article, so the brief covers its first part.</p>}
        <p>
          {data.mode === "ai"
            ? "Written by AI from the article's text. It can miss nuance, so check the original before you rely on it."
            : "Key sentences picked from the article by BlitzFeed's summarizer."}
        </p>
      </div>
    </div>
  );
}

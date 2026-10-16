import Link from "next/link";
import { callBackend } from "@/lib/server";

export const metadata = {
  title: "How BlitzFeed works",
  description: "How BlitzFeed picks stories, writes briefs, and handles your data.",
};

const STEPS = [
  {
    title: "We gather the headlines",
    body: "Every few minutes BlitzFeed pulls the top stories for your edition from publishers' RSS feeds, groups the same story from different outlets, and sorts them into sections.",
  },
  {
    title: "You ask for a brief",
    body: "Tap “Brief me” on any story. BlitzFeed reads the publisher's page and pulls out the article text, leaving the ads, menus, and comments behind.",
  },
  {
    title: "You get the substance",
    body: "You get a one-line summary, the key points, and why the story matters. Ask follow-up questions, compare how outlets cover it, listen, save, or share.",
  },
];

// Who writes "AI brief" summaries, by the provider the API reports.
const AI_WRITERS = {
  anthropic: { writer: "Claude, an AI model from Anthropic", processor: "Anthropic" },
  groq: { writer: "an open-weight AI model running on Groq", processor: "Groq" },
};

export default async function AboutPage() {
  const { data: health } = await callBackend("health", { timeout: 5000 });
  const provider = health?.ai?.enabled ? health.ai.provider : null;
  const ai = AI_WRITERS[provider] ?? (provider ? { writer: "an AI model", processor: "our AI provider" } : null);

  return (
    <div className="mx-auto max-w-3xl pt-12">
      <p className="eyebrow">How it works</p>
      <h1 className="mt-2 font-serif text-5xl font-semibold leading-[1.05] tracking-[-0.03em] sm:text-6xl">
        Read less. <span className="italic text-accent-ink">Know more.</span>
      </h1>
      <p className="mt-6 max-w-[60ch] text-lg leading-relaxed text-muted">
        BlitzFeed turns the day&apos;s headlines into short, accurate briefs so you can follow the news in minutes and dive deeper
        only when a story deserves it.
      </p>

      <ol className="mt-14 grid gap-10 sm:grid-cols-3 sm:gap-8">
        {STEPS.map((step, index) => (
          <li key={step.title}>
            <span className="font-serif text-4xl font-semibold text-accent-ink tabular-nums">{index + 1}</span>
            <h2 className="mt-2 font-semibold">{step.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>
          </li>
        ))}
      </ol>

      <section className="mt-16 rounded-2xl bg-surface p-7 ring-1 ring-line">
        <h2 className="font-serif text-2xl font-semibold tracking-tight">About the summaries</h2>
        <div className="mt-3 space-y-3 text-[15px] leading-relaxed text-muted">
          <p>
            {ai && (
              <>
                Briefs labelled <strong className="text-fg">AI brief</strong> are written by {ai.writer}, using only the
                article&apos;s own text.{" "}
              </>
            )}
            Briefs labelled <strong className="text-fg">Quick summary</strong> are built by BlitzFeed&apos;s own summarizer, which
            picks the most central sentences straight from the article.
            {ai && " When the AI service is busy, you get a quick summary instead."}
          </p>
          <p>
            Either way, a summary can miss nuance or context. Every brief links to the original story, so check it before you rely on
            or share something important. Some publishers block automated reading or sit behind paywalls; for those, we send you to
            the source instead.
          </p>
        </div>
      </section>

      <section id="privacy" className="mt-8 scroll-mt-32 rounded-2xl bg-surface p-7 ring-1 ring-line">
        <h2 className="font-serif text-2xl font-semibold tracking-tight">Privacy</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-muted">
          <li>There are no accounts, and we don&apos;t use tracking or advertising cookies.</li>
          <li>Saved stories and your theme live only in your browser. Clearing your browser data removes them.</li>
          <li>We store one cookie to remember your edition (United States or India).</li>
          <li>Listening uses your device&apos;s built-in voices, so audio never leaves your device.</li>
          <li>
            To make a brief, our server fetches the public article page
            {ai ? `; article text and your questions sent for AI features are processed by ${ai.processor}.` : "."}
          </li>
        </ul>
      </section>

      <div className="mt-12 flex flex-wrap gap-3">
        <Link href="/" className="btn-primary">
          Read today&apos;s stories
        </Link>
        <Link href="/search" className="btn-secondary">
          Search the news
        </Link>
      </div>
    </div>
  );
}

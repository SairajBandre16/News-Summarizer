"use client";

import { useId, useState } from "react";
import { ArrowUpRightIcon, ChatBubbleLeftRightIcon, ScaleIcon, SparklesIcon } from "@heroicons/react/20/solid";
import { useReader } from "./ReaderContext";

const SUGGESTIONS = ["What happens next?", "Who is affected?", "What are the key numbers?"];
const STORY_FIELDS = ["id", "title", "source", "url", "sig", "publishedAt", "summarizable"];

function pick(story) {
  return Object.fromEntries(STORY_FIELDS.map((field) => [field, story[field]]));
}

async function post(path, body) {
  let response;
  try {
    response = await fetch(`/api/${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Check your connection and try again.");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.error?.message || "Something went wrong. Please try again.");
  return data;
}

function Answer({ item }) {
  if (item.pending) {
    return (
      <div className="space-y-2" aria-hidden="true">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
      </div>
    );
  }
  if (item.error) return <p className="text-sm text-negative">{item.error}</p>;

  const { data } = item;
  if (data.mode === "ai") {
    return (
      <div className="space-y-2.5">
        <p className={`text-[15px] leading-relaxed ${data.answerable ? "" : "text-muted"}`}>{data.answer}</p>
        {data.quote && (
          <blockquote className="border-l-2 border-line pl-3 font-serif text-[15px] italic leading-relaxed text-fg/80">
            &ldquo;{data.quote}&rdquo;
          </blockquote>
        )}
      </div>
    );
  }
  return (
    <div className="space-y-2.5">
      {data.notice && <p className="text-xs text-muted">{data.notice}</p>}
      {data.passages.length > 0 ? (
        <>
          <p className="text-xs font-semibold text-muted">Closest passages in the article</p>
          {data.passages.map((passage, index) => (
            <blockquote key={index} className="border-l-2 border-line pl-3 text-[15px] leading-relaxed">
              {passage}
            </blockquote>
          ))}
        </>
      ) : (
        <p className="text-[15px] leading-relaxed text-muted">The article doesn&apos;t seem to mention that.</p>
      )}
    </div>
  );
}

/** Follow-up questions answered only from the article's own text. */
export function AskStory({ article }) {
  const inputId = useId();
  const [question, setQuestion] = useState("");
  const [thread, setThread] = useState([]);
  const busy = thread.some((item) => item.pending);

  async function ask(text) {
    const value = text.trim();
    if (value.length < 3 || busy) return;
    const key = Date.now();
    setQuestion("");
    setThread((items) => [...items, { key, question: value, pending: true }]);
    try {
      const data = await post("ask", { url: article.url, sig: article.sig, question: value });
      setThread((items) => items.map((item) => (item.key === key ? { key, question: value, data } : item)));
    } catch (error) {
      setThread((items) => items.map((item) => (item.key === key ? { key, question: value, error: error.message } : item)));
    }
  }

  return (
    <section aria-labelledby={`${inputId}-title`} className="border-t border-line pt-8">
      <h3 id={`${inputId}-title`} className="flex items-center gap-2 font-semibold">
        <ChatBubbleLeftRightIcon className="size-4 text-accent-ink" />
        Ask about this story
      </h3>
      <p className="mt-1 text-sm text-muted">Answers come only from the article, with a quote when there is one.</p>

      {thread.length > 0 && (
        <ol className="mt-5 space-y-5" aria-live="polite">
          {thread.map((item) => (
            <li key={item.key} className="space-y-2">
              <p className="text-sm font-semibold">{item.question}</p>
              <Answer item={item} />
            </li>
          ))}
        </ol>
      )}

      <form
        className="mt-5 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          ask(question);
        }}
      >
        <label htmlFor={inputId} className="sr-only">
          Your question about this story
        </label>
        <input
          id={inputId}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={300}
          autoComplete="off"
          placeholder="Ask a question"
          className="h-10 min-w-0 flex-1 rounded-full border border-line bg-surface px-4 text-sm text-fg outline-none transition placeholder:text-muted focus:border-accent focus:ring-4 focus:ring-accent/15"
        />
        <button type="submit" className="btn-secondary" disabled={busy || question.trim().length < 3}>
          Ask
        </button>
      </form>
      {thread.length === 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button key={suggestion} type="button" className="tag" onClick={() => ask(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function List({ title, items }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="eyebrow">{title}</p>
      <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[15px] leading-relaxed marker:text-accent">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function Comparison({ data }) {
  const ai = data.mode === "ai";
  return (
    <div className="mt-5 space-y-6">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        <span
          className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 font-semibold ${
            ai ? "bg-accent/15 text-accent-ink" : "bg-surface-2 text-fg/80"
          }`}
        >
          {ai && <SparklesIcon className="size-3.5" />}
          {ai ? "AI comparison" : "Quick comparison"}
        </span>
        {data.skipped > 0 && <span>{data.skipped} outlet couldn&apos;t be read and was left out.</span>}
      </div>
      {data.notice && <p className="text-xs text-muted">{data.notice}</p>}
      {data.sameEvent === false && (
        <p className="rounded-lg bg-surface-2/70 px-3 py-2 text-sm">
          These stories look like they cover different events, so take the comparison loosely.
        </p>
      )}
      {data.event && <p className="font-serif text-xl leading-snug">{data.event}</p>}
      <List title="What every outlet reports" items={data.commonGround} />
      <div>
        <p className="eyebrow">{ai ? "How each outlet tells it" : "How each outlet opens the story"}</p>
        <ul className="mt-3 space-y-4">
          {data.outlets.map((outlet) => (
            <li key={outlet.url} className="rounded-xl bg-surface-2/60 p-4">
              <a
                href={outlet.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm font-semibold hover:text-accent-ink"
              >
                {outlet.source}
                <ArrowUpRightIcon className="size-3.5" />
              </a>
              {outlet.angle && <p className="mt-1.5 text-[15px] leading-relaxed">{outlet.angle}</p>}
              {outlet.unique?.length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-relaxed text-fg/80">
                  {outlet.unique.map((fact, index) => (
                    <li key={index}>Only here: {fact}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </div>
      <List title="Where they differ" items={data.differences} />
      {ai && <p className="text-xs leading-relaxed text-muted">Written by AI from each article&apos;s text. It describes framing, not who is right.</p>}
    </div>
  );
}

/** Other outlets' versions of the same story, and a side-by-side comparison. */
export function Coverage({ article }) {
  const { open } = useReader();
  const [state, setState] = useState({});
  const related = article.related ?? [];
  if (related.length === 0) return null;

  const comparable = [article, ...related].filter((story) => story.summarizable).slice(0, 4);

  async function compare() {
    setState({ pending: true });
    try {
      const data = await post("compare", { stories: comparable.map(({ url, sig }) => ({ url, sig })) });
      setState({ data });
    } catch (error) {
      setState({ error: error.message });
    }
  }

  return (
    <section className="border-t border-line pt-8">
      <h3 className="flex items-center gap-2 font-semibold">
        <ScaleIcon className="size-4 text-accent-ink" />
        {related.length + 1} outlets cover this story
      </h3>
      <ul className="mt-4 divide-y divide-line">
        {related.map((story) => (
          <li key={story.id} className="flex items-start gap-3 py-3 first:pt-0">
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-fg/80">{story.source}</p>
              <a
                href={story.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-0.5 block text-[15px] leading-snug hover:text-accent-ink"
              >
                {story.title}
              </a>
            </div>
            {story.summarizable && (
              <button
                type="button"
                className="btn-ghost shrink-0 py-1 text-xs"
                // Keep the other outlets one tap away from the version being read.
                onClick={() => open({ ...story, related: [pick(article), ...related.filter((r) => r.id !== story.id)] })}
              >
                Brief
              </button>
            )}
          </li>
        ))}
      </ul>

      {comparable.length >= 2 && !state.data && (
        <button type="button" className="btn-secondary mt-4" onClick={compare} disabled={state.pending}>
          <ScaleIcon className="size-4" />
          {state.pending ? "Comparing coverage…" : "Compare how outlets cover it"}
        </button>
      )}
      {state.pending && (
        <div className="mt-5 space-y-2" aria-hidden="true">
          <div className="skeleton h-5 w-full" />
          <div className="skeleton h-5 w-2/3" />
          <div className="skeleton mt-4 h-20 w-full rounded-xl" />
        </div>
      )}
      {state.error && <p className="mt-3 text-sm text-negative">{state.error}</p>}
      <div aria-live="polite">{state.data && <Comparison data={state.data} />}</div>
    </section>
  );
}

import { createHash } from "node:crypto";
import { cache } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowUpRightIcon } from "@heroicons/react/20/solid";
import BriefActions from "@/components/BriefActions";
import { StateMessage } from "@/components/States";
import SummaryView from "@/components/SummaryView";
import Thumbnail from "@/components/Thumbnail";
import { callBackend } from "@/lib/server";

// Shared by generateMetadata and the page so the summary is requested once.
const getBrief = cache((url, sig) =>
  callBackend("summarize", { method: "POST", body: { url, sig }, timeout: 60000 }),
);

function readParams(params) {
  const url = typeof params.u === "string" ? params.u : "";
  const sig = typeof params.s === "string" ? params.s : "";
  return /^https?:\/\//.test(url) && sig ? { url, sig } : null;
}

export async function generateMetadata({ searchParams }) {
  const params = readParams(await searchParams);
  if (!params) return {};
  const { data } = await getBrief(params.url, params.sig);
  if (!data) return { title: "Story brief", robots: { index: false } };
  return {
    title: data.title || "Story brief",
    description: data.summary.tldr,
    robots: { index: false },
    openGraph: { title: data.title, description: data.summary.tldr, images: data.image ? [data.image] : undefined },
  };
}

export default async function BriefPage({ searchParams }) {
  const params = readParams(await searchParams);
  if (!params) notFound();
  const { data, error } = await getBrief(params.url, params.sig);

  if (error) {
    return (
      <StateMessage
        tone="error"
        title="We couldn't open this brief"
        actions={
          <>
            <a href={params.url} target="_blank" rel="noopener noreferrer" className="btn-primary">
              Read the original
              <ArrowUpRightIcon className="size-4" />
            </a>
            <Link href="/" className="btn-secondary">
              Today&apos;s stories
            </Link>
          </>
        }
      >
        {error.message}
      </StateMessage>
    );
  }

  const source = data.siteName || new URL(params.url).hostname.replace(/^www\./, "");
  const article = {
    id: createHash("sha1").update(params.url).digest("hex").slice(0, 16),
    title: data.title || "Untitled story",
    description: data.summary.tldr,
    url: params.url,
    sig: params.sig,
    image: data.image,
    source,
    publishedAt: data.publishedAt,
    summarizable: true,
  };

  return (
    <article className="mx-auto max-w-2xl pt-10">
      <p className="text-xs text-muted">
        <span className="font-semibold text-fg/80">{source}</span>
        {data.author && <> · {data.author}</>}
      </p>
      <h1 className="mt-2 font-serif text-4xl font-semibold leading-[1.1] tracking-[-0.025em] sm:text-5xl">{article.title}</h1>
      {data.image && <Thumbnail src={data.image} alt="" source={source} priority className="mt-6 aspect-[16/9] w-full rounded-2xl" />}
      <BriefActions article={article} summary={data.summary} />
      <div className="mt-8">
        <SummaryView data={data} />
      </div>
      <div className="mt-10 flex flex-col gap-3 border-t border-line pt-8 sm:flex-row">
        <a href={params.url} target="_blank" rel="noopener noreferrer" className="btn-primary flex-1">
          Read the full story at {source}
          <ArrowUpRightIcon className="size-4" />
        </a>
        <Link href="/" className="btn-secondary">
          More briefs on BlitzFeed
        </Link>
      </div>
    </article>
  );
}

import { Suspense } from "react";
import { PAGE_SIZE } from "@/lib/constants";
import { timeAgo } from "@/lib/format";
import { callBackend } from "@/lib/server";
import ArticleCard from "./ArticleCard";
import ArticleGrid from "./ArticleGrid";
import Briefing from "./Briefing";
import LoadMore from "./LoadMore";
import RetryButton from "./RetryButton";
import { BriefingSkeleton } from "./Skeletons";
import { SectionHeading, StateMessage } from "./States";

const SIDE_COUNT = 3;

export default async function Feed({ edition, category, withBriefing = false }) {
  // Lead story + (briefing or 3 side stories) + a full grid page.
  const limit = 1 + (withBriefing ? 0 : SIDE_COUNT) + PAGE_SIZE;
  const { data, error } = await callBackend("news", { params: { edition, category, limit } });

  if (error) {
    return (
      <StateMessage tone="error" title="We couldn't load the news" actions={<RetryButton />}>
        {error.message}
      </StateMessage>
    );
  }
  if (!data.articles.length) {
    return (
      <StateMessage title="No stories here yet">
        There aren&apos;t any stories in this section right now. Try another section or edition.
      </StateMessage>
    );
  }

  const [lead, ...rest] = data.articles;
  const side = withBriefing ? [] : rest.slice(0, SIDE_COUNT);
  const grid = withBriefing ? rest : rest.slice(SIDE_COUNT);

  return (
    <>
      <p className="mt-4 text-xs text-muted" suppressHydrationWarning>
        {data.stale
          ? "We're having trouble reaching our news provider, so you're seeing an earlier edition."
          : `Updated ${timeAgo(data.fetchedAt).toLowerCase()}`}
      </p>

      <section className="grid gap-12 pt-6 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <ArticleCard article={lead} variant="lead" priority />
        </div>
        <aside className="lg:col-span-5" aria-label={withBriefing ? "Daily briefing" : "Latest stories"}>
          {withBriefing ? (
            <Suspense fallback={<BriefingSkeleton />}>
              <Briefing edition={edition} />
            </Suspense>
          ) : (
            <div className="flex flex-col gap-5">
              <h2 className="eyebrow">Latest</h2>
              {side.map((article, index) => (
                <ArticleCard key={article.id} article={article} variant="compact" index={index + 1} />
              ))}
            </div>
          )}
        </aside>
      </section>

      {grid.length > 0 && (
        <>
          <SectionHeading>More stories</SectionHeading>
          <ArticleGrid articles={grid} />
        </>
      )}
      <LoadMore
        endpoint="news"
        params={{ edition, category }}
        offset={data.articles.length}
        hasMore={data.hasMore}
        renderedIds={data.articles.map((a) => a.id)}
      />
    </>
  );
}

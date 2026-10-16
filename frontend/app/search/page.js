import { Suspense } from "react";
import Link from "next/link";
import ArticleGrid from "@/components/ArticleGrid";
import LoadMore from "@/components/LoadMore";
import RetryButton from "@/components/RetryButton";
import SearchForm from "@/components/SearchForm";
import { GridSkeleton } from "@/components/Skeletons";
import { StateMessage } from "@/components/States";
import { PAGE_SIZE, editionLabel } from "@/lib/constants";
import { callBackend, getEdition } from "@/lib/server";

const SORTS = [
  { id: "publishedAt", label: "Latest" },
  { id: "relevancy", label: "Most relevant" },
  { id: "popularity", label: "Popular" },
];

const SUGGESTIONS = ["Artificial intelligence", "Climate", "Interest rates", "Electric vehicles", "Cricket", "Space"];

function cleanQuery(value) {
  return String(Array.isArray(value) ? value[0] : value ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 200);
}

export async function generateMetadata({ searchParams }) {
  const query = cleanQuery((await searchParams).q);
  return { title: query ? `“${query}”` : "Search", robots: { index: false } };
}

export default async function SearchPage({ searchParams }) {
  const params = await searchParams;
  const query = cleanQuery(params.q);
  const sort = SORTS.some((s) => s.id === params.sort) ? params.sort : "publishedAt";
  const edition = await getEdition();

  return (
    <div className="pt-10">
      <h1 className="font-serif text-4xl font-semibold tracking-[-0.025em] sm:text-5xl">
        {query ? <>Results for “{query}”</> : "Search the news"}
      </h1>
      <SearchForm key={query} large defaultValue={query} autoFocus={!query} className="mt-6 max-w-2xl" />

      {query ? (
        <>
          <nav aria-label="Sort results" className="mt-6 flex flex-wrap items-center gap-2 border-b border-line pb-5">
            {SORTS.map((option) => {
              const active = option.id === sort;
              return (
                <Link
                  key={option.id}
                  href={{ pathname: "/search", query: { q: query, sort: option.id } }}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
                    active ? "bg-fg text-bg" : "text-muted ring-1 ring-line hover:text-fg"
                  }`}
                >
                  {option.label}
                </Link>
              );
            })}
            <span className="ml-auto text-xs text-muted">{editionLabel(edition)} edition</span>
          </nav>
          <Suspense key={`${query}:${sort}:${edition}`} fallback={<div className="mt-10"><GridSkeleton /></div>}>
            <Results query={query} sort={sort} edition={edition} />
          </Suspense>
        </>
      ) : (
        <div className="mt-10">
          <h2 className="eyebrow">Try a topic</h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((topic) => (
              <li key={topic}>
                <Link href={{ pathname: "/search", query: { q: topic } }} className="btn-secondary">
                  {topic}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

async function Results({ query, sort, edition }) {
  const { data, error } = await callBackend("search", { params: { q: query, sort, edition, limit: PAGE_SIZE } });

  if (error) {
    return (
      <StateMessage tone="error" title="Search isn't working right now" actions={<RetryButton />}>
        {error.message}
      </StateMessage>
    );
  }
  if (!data.articles.length) {
    return (
      <StateMessage title="No stories found">
        Nothing matched “{query}”. Try fewer or broader words, or check the spelling.
      </StateMessage>
    );
  }

  return (
    <div className="mt-10">
      <p className="mb-8 text-sm text-muted">
        {data.total === 1 ? "1 story" : `${data.total} stories`}
      </p>
      <ArticleGrid articles={data.articles} />
      <LoadMore
        endpoint="search"
        params={{ q: query, sort, edition }}
        offset={data.articles.length}
        hasMore={data.hasMore}
        renderedIds={data.articles.map((a) => a.id)}
      />
    </div>
  );
}

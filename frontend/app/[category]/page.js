import { Suspense } from "react";
import { notFound } from "next/navigation";
import Feed from "@/components/Feed";
import { FeedSkeleton } from "@/components/Skeletons";
import { PageHeading } from "@/components/States";
import { CATEGORIES, editionLabel } from "@/lib/constants";
import { getEdition } from "@/lib/server";

function findCategory(id) {
  return CATEGORIES.find((c) => c.id === id && c.id !== "general");
}

export async function generateMetadata({ params }) {
  const category = findCategory((await params).category);
  if (!category) return {};
  return { title: category.label, description: `${category.blurb} Summarized by BlitzFeed.` };
}

export default async function CategoryPage({ params }) {
  const category = findCategory((await params).category);
  if (!category) notFound();
  const edition = await getEdition();

  return (
    <>
      <PageHeading eyebrow={`${editionLabel(edition)} edition`} title={category.label}>
        {category.blurb}
      </PageHeading>
      <Suspense key={`${edition}:${category.id}`} fallback={<FeedSkeleton />}>
        <Feed edition={edition} category={category.id} />
      </Suspense>
    </>
  );
}

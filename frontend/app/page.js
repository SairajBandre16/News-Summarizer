import { Suspense } from "react";
import Feed from "@/components/Feed";
import LocalDate from "@/components/LocalDate";
import { FeedSkeleton } from "@/components/Skeletons";
import { PageHeading } from "@/components/States";
import { editionLabel } from "@/lib/constants";
import { getEdition } from "@/lib/server";

export default async function HomePage() {
  const edition = await getEdition();

  return (
    <>
      <PageHeading eyebrow={<LocalDate />} title="Today's top stories">
        {editionLabel(edition)} edition
      </PageHeading>
      <Suspense key={edition} fallback={<FeedSkeleton withBriefing />}>
        <Feed edition={edition} category="general" withBriefing />
      </Suspense>
    </>
  );
}

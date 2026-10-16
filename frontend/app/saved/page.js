import SavedStories from "@/components/SavedStories";
import { PageHeading } from "@/components/States";

export const metadata = { title: "Saved stories", robots: { index: false } };

export default function SavedPage() {
  return (
    <>
      <PageHeading eyebrow="Your reading list" title="Saved stories">
        Saved stories stay on this device. Nothing is sent to our servers.
      </PageHeading>
      <SavedStories />
    </>
  );
}

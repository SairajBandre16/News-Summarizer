import { callBackend } from "@/lib/server";
import BriefingCard from "./BriefingCard";

export default async function Briefing({ edition }) {
  // A cold AI briefing can take a few seconds; it streams in behind a skeleton.
  const { data } = await callBackend("briefing", { params: { edition }, timeout: 60000 });

  if (!data?.items?.length) {
    return (
      <div className="flex h-full flex-col justify-center rounded-2xl bg-surface p-7 ring-1 ring-line">
        <p className="eyebrow">Today in 60 seconds</p>
        <p className="mt-2 font-serif text-xl">The briefing is taking a break.</p>
        <p className="mt-1 text-sm text-muted">It will be back shortly. The latest stories are below.</p>
      </div>
    );
  }
  return <BriefingCard briefing={data} />;
}

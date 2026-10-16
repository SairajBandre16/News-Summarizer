import { SummarySkeleton } from "@/components/Skeletons";

export default function Loading() {
  return (
    <div className="mx-auto max-w-2xl pt-10" aria-busy="true" aria-label="Loading brief">
      <div className="skeleton h-3 w-32" />
      <div className="skeleton mt-4 h-10 w-full" />
      <div className="skeleton mt-2 h-10 w-3/4" />
      <div className="skeleton mt-6 aspect-[16/9] w-full rounded-2xl" />
      <p className="mt-8 text-sm text-muted">Reading the article and writing your brief…</p>
      <div className="mt-6">
        <SummarySkeleton />
      </div>
    </div>
  );
}

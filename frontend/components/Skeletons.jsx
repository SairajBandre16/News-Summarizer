function CardSkeleton() {
  return (
    <div>
      <div className="skeleton aspect-[3/2] w-full rounded-xl" />
      <div className="skeleton mt-4 h-3 w-1/3" />
      <div className="skeleton mt-3 h-5 w-full" />
      <div className="skeleton mt-2 h-5 w-4/5" />
      <div className="skeleton mt-3 h-3 w-2/3" />
    </div>
  );
}

export function GridSkeleton({ count = 6 }) {
  return (
    <div className="grid gap-x-7 gap-y-12 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

export function BriefingSkeleton() {
  return (
    <div className="rounded-2xl bg-surface p-6 ring-1 ring-line" aria-hidden="true">
      <div className="skeleton h-4 w-40" />
      <div className="skeleton mt-4 h-6 w-full" />
      <div className="skeleton mt-2 h-6 w-2/3" />
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="mt-6 flex gap-3">
          <div className="skeleton size-6 shrink-0" />
          <div className="flex-1">
            <div className="skeleton h-4 w-full" />
            <div className="skeleton mt-2 h-3 w-4/5" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function FeedSkeleton({ withBriefing = false }) {
  return (
    <div aria-busy="true" aria-label="Loading stories">
      <div className="grid gap-10 pt-8 lg:grid-cols-12 lg:gap-12" aria-hidden="true">
        <div className="lg:col-span-7">
          <div className="skeleton aspect-[16/10] w-full rounded-2xl" />
          <div className="skeleton mt-5 h-3 w-1/4" />
          <div className="skeleton mt-3 h-9 w-full" />
          <div className="skeleton mt-2 h-9 w-3/4" />
          <div className="skeleton mt-4 h-4 w-5/6" />
        </div>
        <div className="lg:col-span-5">
          {withBriefing ? (
            <BriefingSkeleton />
          ) : (
            <div className="space-y-6">
              {Array.from({ length: 3 }, (_, i) => (
                <div key={i} className="flex gap-4">
                  <div className="flex-1">
                    <div className="skeleton h-3 w-1/3" />
                    <div className="skeleton mt-3 h-5 w-full" />
                    <div className="skeleton mt-2 h-5 w-2/3" />
                  </div>
                  <div className="skeleton size-24 rounded-xl" />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="mt-16">
        <GridSkeleton />
      </div>
    </div>
  );
}

export function SummarySkeleton() {
  return (
    <div aria-hidden="true" className="space-y-7">
      <div>
        <div className="skeleton h-3 w-28" />
        <div className="skeleton mt-3 h-6 w-full" />
        <div className="skeleton mt-2 h-6 w-5/6" />
      </div>
      <div className="space-y-4">
        <div className="skeleton h-3 w-20" />
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="flex gap-3">
            <div className="skeleton size-5 shrink-0" />
            <div className="skeleton h-4 flex-1" />
          </div>
        ))}
      </div>
      <div className="skeleton h-20 w-full rounded-xl" />
    </div>
  );
}

"use client";

import { useMounted } from "@/lib/hooks";

const format = new Intl.DateTimeFormat("en", { weekday: "long", month: "long", day: "numeric" });

/** Today's date in the reader's own timezone (rendered after hydration). */
export default function LocalDate() {
  const mounted = useMounted();
  return <span className="inline-block min-w-[10ch]">{mounted ? format.format(new Date()) : " "}</span>;
}

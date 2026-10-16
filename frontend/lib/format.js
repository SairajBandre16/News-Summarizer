const dayFormat = new Intl.DateTimeFormat("en", { month: "short", day: "numeric" });

export function timeAgo(iso, now = Date.now()) {
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return "";
  const minutes = Math.round((now - time) / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return dayFormat.format(time);
}

export function briefUrl(origin, article) {
  const params = new URLSearchParams({ u: article.url, s: article.sig });
  return `${origin}/brief?${params}`;
}

/** Text the Listen button reads aloud for an article brief. */
export function briefToSpeech(title, summary) {
  const parts = [title, summary.tldr];
  if (summary.keyPoints?.length) parts.push("Key points.", ...summary.keyPoints);
  if (summary.whyItMatters) parts.push("Why it matters.", summary.whyItMatters);
  return parts.join(" ");
}

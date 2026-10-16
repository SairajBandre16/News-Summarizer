export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const EDITION_COOKIE = "bf_edition";

export const EDITIONS = [
  { id: "us", label: "United States", short: "US" },
  { id: "in", label: "India", short: "IN" },
];

export const CATEGORIES = [
  { id: "general", label: "Top stories", href: "/", blurb: "The day's most important headlines." },
  { id: "business", label: "Business", href: "/business", blurb: "Markets, companies, and the economy." },
  { id: "technology", label: "Technology", href: "/technology", blurb: "AI, gadgets, software, and the companies building them." },
  { id: "science", label: "Science", href: "/science", blurb: "Space, climate, research, and discovery." },
  { id: "health", label: "Health", href: "/health", blurb: "Medicine, wellbeing, and public health." },
  { id: "sports", label: "Sports", href: "/sports", blurb: "Results, transfers, and the stories behind the games." },
  { id: "entertainment", label: "Entertainment", href: "/entertainment", blurb: "Film, TV, music, and culture." },
];

// Grid pages load in multiples of 6 so rows stay full at 2 and 3 columns.
export const PAGE_SIZE = 18;

export function editionLabel(id) {
  return EDITIONS.find((e) => e.id === id)?.label ?? id;
}

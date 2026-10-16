import { BRAND } from "@/lib/brand-image";

export default function manifest() {
  return {
    name: "BlitzFeed",
    short_name: "BlitzFeed",
    description: "The day's top headlines, briefed.",
    start_url: "/",
    display: "standalone",
    background_color: BRAND.paper,
    theme_color: BRAND.paper,
    icons: [
      { src: "/icons/192", sizes: "192x192", type: "image/png" },
      { src: "/icons/512", sizes: "512x512", type: "image/png" },
      { src: "/icons/512", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}

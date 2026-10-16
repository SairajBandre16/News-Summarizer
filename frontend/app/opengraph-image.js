import { ImageResponse } from "next/og";
import { BRAND } from "@/lib/brand-image";

export const alt = "BlitzFeed: the news, briefed";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 80,
          background: `radial-gradient(circle at 85% 15%, #F6C9A8 0%, ${BRAND.paper} 55%)`,
          color: BRAND.ink,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div style={{ width: 96, height: 96, borderRadius: 26, background: BRAND.accent, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width="60" height="60" viewBox="0 0 32 32">
              <path d="M18.6 5 8.8 18.2h6.3L13.4 27l9.8-13.2h-6.3L18.6 5Z" fill={BRAND.ink} />
            </svg>
          </div>
          <div style={{ fontSize: 64, fontWeight: 700, letterSpacing: -2 }}>BlitzFeed</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 92, fontWeight: 700, letterSpacing: -3, lineHeight: 1 }}>Read less. Know more.</div>
          <div style={{ fontSize: 36, color: "#6B5D52" }}>Top headlines with instant briefs you can read or listen to.</div>
        </div>
      </div>
    ),
    size,
  );
}

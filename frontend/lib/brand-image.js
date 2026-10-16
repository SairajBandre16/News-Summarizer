import { ImageResponse } from "next/og";

export const BRAND = { accent: "#EA783E", ink: "#2B1A12", paper: "#FAF8F4" };

/** The bolt mark as a PNG at any size, used for app icons. */
export function iconResponse(size) {
  const radius = Math.round(size * 0.28);
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: BRAND.accent, borderRadius: radius }}>
        <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 32 32">
          <path d="M18.6 5 8.8 18.2h6.3L13.4 27l9.8-13.2h-6.3L18.6 5Z" fill={BRAND.ink} />
        </svg>
      </div>
    ),
    { width: size, height: size },
  );
}

"use client";

import { useState } from "react";
import { LogoMark } from "./Logo";

export default function Thumbnail({ src, alt, source, className = "", priority = false, compact = false }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <div
        aria-hidden="true"
        className={`placeholder-art relative flex flex-col items-center justify-center overflow-hidden ${compact ? "p-2" : "gap-3 p-6"} ${className}`}
      >
        {!compact && <LogoMark className="size-6 opacity-80" />}
        <span
          className={`line-clamp-2 max-w-[18ch] text-center font-serif font-medium italic leading-tight text-fg/75 ${compact ? "text-sm" : "text-2xl"}`}
        >
          {source || "BlitzFeed"}
        </span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : "auto"}
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      // Catch images that already failed before hydration attached onError.
      ref={(img) => {
        if (img?.complete && img.naturalWidth === 0) setFailed(true);
      }}
      className={`bg-surface-2 object-cover ${className}`}
    />
  );
}

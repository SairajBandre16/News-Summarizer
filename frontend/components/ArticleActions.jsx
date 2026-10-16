"use client";

import { useState } from "react";
import { BookmarkIcon as BookmarkOutline, CheckIcon, ShareIcon, SpeakerWaveIcon, StopIcon } from "@heroicons/react/24/outline";
import { BookmarkIcon as BookmarkSolid } from "@heroicons/react/24/solid";
import { useSaved, useSpeech } from "@/lib/hooks";

export function SaveButton({ article, withLabel = false, className = "" }) {
  const { isSaved, toggle } = useSaved();
  const saved = isSaved(article.id);
  const Icon = saved ? BookmarkSolid : BookmarkOutline;
  const label = saved ? "Saved" : "Save";

  return (
    <button
      type="button"
      onClick={() => toggle(article)}
      aria-pressed={saved}
      aria-label={withLabel ? undefined : saved ? "Remove from saved stories" : "Save story"}
      className={`${withLabel ? "btn-ghost" : "icon-btn"} ${saved ? "text-accent-ink" : ""} ${className}`}
    >
      <Icon className="size-5" />
      {withLabel && <span>{label}</span>}
    </button>
  );
}

export function ShareButton({ title, getUrl, withLabel = false, className = "" }) {
  const [copied, setCopied] = useState(false);

  async function share() {
    const url = getUrl();
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
        return;
      } catch (error) {
        if (error?.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }

  const Icon = copied ? CheckIcon : ShareIcon;
  return (
    <button
      type="button"
      onClick={share}
      aria-label={withLabel ? undefined : "Share"}
      className={`${withLabel ? "btn-ghost" : "icon-btn"} ${className}`}
    >
      <Icon className="size-5" />
      {withLabel && <span aria-live="polite">{copied ? "Link copied" : "Share"}</span>}
    </button>
  );
}

export function ListenButton({ getText, label = "Listen", className = "" }) {
  const { supported, speaking, speak, stop } = useSpeech();
  if (!supported) return null;

  return (
    <button
      type="button"
      aria-pressed={speaking}
      onClick={() => (speaking ? stop() : speak(getText()))}
      className={`btn-secondary ${speaking ? "ring-accent" : ""} ${className}`}
    >
      {speaking ? <StopIcon className="size-4" /> : <SpeakerWaveIcon className="size-4" />}
      <span>{speaking ? "Stop" : label}</span>
      {speaking && (
        <span aria-hidden="true" className="flex h-3 items-end gap-0.5">
          {[0, 1, 2].map((bar) => (
            <span
              key={bar}
              className="w-0.5 animate-pulse rounded-full bg-accent"
              style={{ height: `${6 + bar * 3}px`, animationDelay: `${bar * 150}ms` }}
            />
          ))}
        </span>
      )}
    </button>
  );
}

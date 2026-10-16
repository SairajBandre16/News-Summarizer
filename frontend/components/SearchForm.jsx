"use client";

import Form from "next/form";
import { useEffect, useId, useRef } from "react";
import { MagnifyingGlassIcon } from "@heroicons/react/20/solid";

export default function SearchForm({ className = "", defaultValue = "", autoFocus = false, shortcut = false, large = false }) {
  const inputRef = useRef(null);
  const id = useId();

  useEffect(() => {
    if (!shortcut) return;
    function onKeyDown(event) {
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target;
      if (target instanceof HTMLElement && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
      event.preventDefault();
      inputRef.current?.focus();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [shortcut]);

  return (
    <Form action="/search" role="search" className={`relative ${className}`}>
      <label htmlFor={id} className="sr-only">
        Search the news
      </label>
      <MagnifyingGlassIcon
        className={`pointer-events-none absolute top-1/2 -translate-y-1/2 text-muted ${large ? "left-4 size-5" : "left-3 size-4"}`}
      />
      <input
        ref={inputRef}
        id={id}
        name="q"
        type="search"
        required
        maxLength={200}
        autoComplete="off"
        defaultValue={defaultValue}
        autoFocus={autoFocus}
        placeholder={large ? "Search for a topic, person, or company" : "Search the news"}
        className={`w-full rounded-full border border-line bg-surface text-fg outline-none transition placeholder:text-muted focus:border-accent focus:ring-4 focus:ring-accent/15 [&::-webkit-search-cancel-button]:hidden ${
          large ? "h-14 pl-12 pr-5 text-base" : "h-10 pl-9 pr-10 text-sm"
        }`}
      />
      {shortcut && (
        <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border border-line px-1.5 font-sans text-[11px] text-muted">
          /
        </kbd>
      )}
    </Form>
  );
}

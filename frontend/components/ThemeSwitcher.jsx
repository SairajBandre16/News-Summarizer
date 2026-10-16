"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import { CheckIcon, ComputerDesktopIcon, MoonIcon, SunIcon } from "@heroicons/react/24/outline";
import { useMounted } from "@/lib/hooks";

const OPTIONS = [
  { id: "system", label: "Match system", Icon: ComputerDesktopIcon },
  { id: "light", label: "Light", Icon: SunIcon },
  { id: "dark", label: "Dark", Icon: MoonIcon },
];

export default function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const mounted = useMounted();
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    function onKeyDown(event) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const current = OPTIONS.find((o) => o.id === (mounted ? theme : "system")) ?? OPTIONS[0];
  const CurrentIcon = current.Icon;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        className="icon-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Theme: ${current.label}`}
        onClick={() => setOpen((v) => !v)}
      >
        <CurrentIcon className="size-5" />
      </button>
      {open && (
        <div
          role="menu"
          aria-label="Theme"
          className="absolute right-0 top-11 z-40 w-44 animate-rise rounded-xl bg-surface p-1 shadow-[0_12px_40px_-12px_var(--shadow)] ring-1 ring-line"
        >
          {OPTIONS.map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              role="menuitemradio"
              aria-checked={theme === id}
              onClick={() => {
                setTheme(id);
                setOpen(false);
              }}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-fg transition hover:bg-surface-2"
            >
              <Icon className="size-4 text-muted" />
              <span className="flex-1 text-left">{label}</span>
              {theme === id && <CheckIcon className="size-4 text-accent-ink" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

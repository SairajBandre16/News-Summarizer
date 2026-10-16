"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CATEGORIES } from "@/lib/constants";

export default function CategoryNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Sections" className="mx-auto max-w-7xl">
      <ul className="no-scrollbar nav-fade flex gap-1 overflow-x-auto px-2 sm:px-4 lg:px-6">
        {CATEGORIES.map((category) => {
          const active = pathname === category.href;
          return (
            <li key={category.id}>
              <Link
                href={category.href}
                aria-current={active ? "page" : undefined}
                className={`relative block whitespace-nowrap px-2.5 py-3 text-sm font-medium transition-colors after:absolute after:inset-x-2.5 after:bottom-0 after:h-0.5 after:origin-left after:rounded-full after:bg-accent after:transition-transform after:duration-300 ${
                  active ? "text-fg after:scale-x-100" : "text-muted after:scale-x-0 hover:text-fg"
                }`}
              >
                {category.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

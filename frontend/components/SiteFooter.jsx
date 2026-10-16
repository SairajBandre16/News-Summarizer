import Link from "next/link";
import Logo from "./Logo";

const LINKS = [
  { href: "/about", label: "How it works" },
  { href: "/about#privacy", label: "Privacy" },
  { href: "/saved", label: "Saved stories" },
  { href: "/search", label: "Search" },
];

export default function SiteFooter() {
  return (
    <footer className="mt-20 border-t border-line">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 pb-8 pt-10 sm:px-6 md:flex-row md:justify-between lg:px-8">
        <div className="max-w-sm">
          <Logo />
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Read less, know more. The day&apos;s headlines with instant briefs you can read or listen to.
          </p>
        </div>
        <nav aria-label="Footer">
          <ul className="grid grid-cols-2 gap-x-10 gap-y-2 text-sm">
            {LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="text-muted transition hover:text-fg">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <p className="mx-auto max-w-7xl px-4 pb-10 text-xs leading-relaxed text-muted sm:px-6 lg:px-8">
        Headlines from publishers&apos; RSS feeds. Stories belong to their publishers. Summaries are generated automatically and can miss
        nuance, so check the original before you rely on or share them.
      </p>
    </footer>
  );
}

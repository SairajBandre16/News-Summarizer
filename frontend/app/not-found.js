import Link from "next/link";

export const metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center py-24 text-center">
      <p className="font-serif text-8xl font-semibold italic text-accent-ink">404</p>
      <h1 className="mt-4 font-serif text-3xl font-semibold tracking-tight">This page didn&apos;t make the paper</h1>
      <p className="mt-3 text-muted">The link may be broken, or the page may have moved.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link href="/" className="btn-primary">
          Today&apos;s top stories
        </Link>
        <Link href="/search" className="btn-secondary">
          Search the news
        </Link>
      </div>
    </div>
  );
}

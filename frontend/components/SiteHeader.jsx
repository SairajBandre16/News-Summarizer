import Link from "next/link";
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import CategoryNav from "./CategoryNav";
import EditionSwitcher from "./EditionSwitcher";
import Logo from "./Logo";
import SavedLink from "./SavedLink";
import SearchForm from "./SearchForm";
import ThemeSwitcher from "./ThemeSwitcher";

export default function SiteHeader({ edition }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 pt-3 sm:px-6 lg:px-8">
        <Link href="/" aria-label="BlitzFeed home" className="shrink-0 rounded-lg">
          <Logo />
        </Link>
        <div className="hidden flex-1 justify-center md:flex">
          <SearchForm className="w-full max-w-md" shortcut />
        </div>
        <div className="ml-auto flex items-center gap-1 md:ml-0">
          <Link href="/search" className="icon-btn md:hidden" aria-label="Search">
            <MagnifyingGlassIcon className="size-5" />
          </Link>
          <EditionSwitcher current={edition} />
          <ThemeSwitcher />
          <SavedLink />
        </div>
      </div>
      <CategoryNav />
    </header>
  );
}

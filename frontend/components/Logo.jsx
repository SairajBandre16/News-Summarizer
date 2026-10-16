export function LogoMark({ className = "size-8" }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="9" className="fill-accent" />
      <path d="M18.6 5 8.8 18.2h6.3L13.4 27l9.8-13.2h-6.3L18.6 5Z" className="fill-on-accent" />
    </svg>
  );
}

export default function Logo() {
  return (
    <span className="flex items-center gap-2">
      <LogoMark />
      <span className="font-serif text-[1.6rem] font-semibold leading-none tracking-[-0.035em]">BlitzFeed</span>
    </span>
  );
}

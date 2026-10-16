import { ExclamationTriangleIcon, NewspaperIcon } from "@heroicons/react/24/outline";

export function StateMessage({ tone = "neutral", title, children, actions }) {
  const Icon = tone === "error" ? ExclamationTriangleIcon : NewspaperIcon;
  return (
    <div role={tone === "error" ? "alert" : undefined} className="mx-auto flex max-w-md flex-col items-center py-20 text-center">
      <span className={`grid size-12 place-items-center rounded-2xl ${tone === "error" ? "bg-negative/10 text-negative" : "bg-surface-2 text-muted"}`}>
        <Icon className="size-6" />
      </span>
      <h2 className="mt-5 font-serif text-2xl font-semibold tracking-tight">{title}</h2>
      {children && <div className="mt-2 text-sm leading-relaxed text-muted">{children}</div>}
      {actions && <div className="mt-6 flex flex-wrap justify-center gap-3">{actions}</div>}
    </div>
  );
}

export function PageHeading({ eyebrow, title, children }) {
  return (
    <div className="flex flex-col gap-2 border-b border-line pb-6 pt-10 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 className="mt-1 font-serif text-4xl font-semibold tracking-[-0.025em] sm:text-5xl">{title}</h1>
      </div>
      {children && <div className="text-sm text-muted sm:max-w-xs sm:text-right">{children}</div>}
    </div>
  );
}

export function SectionHeading({ children }) {
  return (
    <div className="mb-8 mt-16 flex items-center gap-4">
      <h2 className="shrink-0 font-serif text-2xl font-semibold tracking-tight">{children}</h2>
      <span className="h-px flex-1 bg-line" />
    </div>
  );
}

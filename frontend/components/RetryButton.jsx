"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { ArrowPathIcon } from "@heroicons/react/20/solid";

export default function RetryButton({ onRetry, label = "Try again" }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      className="btn-secondary"
      disabled={pending}
      onClick={() => startTransition(() => (onRetry ? onRetry() : router.refresh()))}
    >
      <ArrowPathIcon className={`size-4 ${pending ? "animate-spin" : ""}`} />
      {label}
    </button>
  );
}

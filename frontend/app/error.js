"use client";

import { useEffect } from "react";
import { StateMessage } from "@/components/States";

export default function Error({ error, reset }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <StateMessage
      tone="error"
      title="Something went wrong"
      actions={
        <button type="button" onClick={reset} className="btn-primary">
          Try again
        </button>
      }
    >
      This page hit an unexpected problem. Trying again usually fixes it.
    </StateMessage>
  );
}

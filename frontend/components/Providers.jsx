"use client";

import { ThemeProvider } from "next-themes";
import { ReaderProvider } from "./ReaderContext";

export default function Providers({ children }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <ReaderProvider>{children}</ReaderProvider>
    </ThemeProvider>
  );
}

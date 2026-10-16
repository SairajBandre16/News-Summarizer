"use client";

import { createContext, useContext, useMemo, useState } from "react";

const ReaderContext = createContext({ article: null, open: () => {}, close: () => {} });

export function ReaderProvider({ children }) {
  const [article, setArticle] = useState(null);
  const value = useMemo(
    () => ({ article, open: setArticle, close: () => setArticle(null) }),
    [article],
  );
  return <ReaderContext value={value}>{children}</ReaderContext>;
}

export function useReader() {
  return useContext(ReaderContext);
}

"use client";

import { briefToSpeech } from "@/lib/format";
import { ListenButton, SaveButton, ShareButton } from "./ArticleActions";

export default function BriefActions({ article, summary }) {
  return (
    <div className="mt-6 flex flex-wrap items-center gap-2">
      <ListenButton getText={() => briefToSpeech(article.title, summary)} label="Listen to brief" />
      <SaveButton article={article} withLabel />
      <ShareButton title={article.title} getUrl={() => window.location.href} withLabel />
    </div>
  );
}

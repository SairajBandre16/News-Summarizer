import ArticleCard from "./ArticleCard";

export default function ArticleGrid({ articles }) {
  return (
    <div className="grid gap-x-7 gap-y-12 sm:grid-cols-2 lg:grid-cols-3">
      {articles.map((article, index) => (
        <ArticleCard key={article.id} article={article} index={index} />
      ))}
    </div>
  );
}

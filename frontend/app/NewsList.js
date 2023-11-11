import Article from './Article';

function NewsList({articles}) {
 
  return articles ? (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 p-10 gap-10">
    {articles.map((article, index) => (
      <Article key={index} article={article}/>
    ))}
    </div>
    ) : (
      <h1 className="p-10 font-serif">No result found.</h1>
    );
}

export default NewsList;

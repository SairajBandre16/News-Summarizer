"use client"
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ReadMoreButton from './ReadMoreButton';
import Loading from './Loading';

function Article({ article }) {
  const [articles, setArticles] = useState([]);

  const getData = async () => {
    try {
      console.log('Fetching news data...');
      const res = await axios.get('http://localhost:8080/allnews');
      console.log('Fetched news data:', res.data);
      const filteredArticles = res.data.filter((article) => article.summary && article.summary.trim() !== '');
      console.log('Filtered articles:', filteredArticles);
      setArticles(filteredArticles);
    } catch (error) {
      console.error('Error fetching news:', error);
    }
  };

  useEffect(() => {
    getData();
    const interval = setInterval(() => {
      getData();
    }, 600000); // 600000 milliseconds = 10 minutes

    return () => clearInterval(interval); // Clear the interval on component unmount
  }, []);

  return articles && articles.length > 0 ? (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 p-10 gap-10">
      {articles.map((article, index) => (
        <article
          key={index}
          className="bg-slate-100 dark:bg-slate-800 flex flex-col rounded-lg shadow-lg hover:scale-105 hover:shadow-xl hover:bg-slate-200 transition-all duration-200 ease-out"
        >
          {article.urlToImage && (
            <img src={article.urlToImage} alt={article.title} className="h-56 w-full object-cover rounded-t-lg shadow-md" />
          )}

          <div className="flex-1 flex flex-col">
            <div className="flex-1 flex flex-col p-5">
              <h2 className="font-bold font-serif ">{article.title}</h2>

              <section className="mt-2 flex-1">
                <p className="text-xs ">{article.summary}</p>
              </section>
            </div>
          </div>
          <ReadMoreButton url={article.url} />
        </article>
      ))}
    </div>
  ) : (
    <Loading/>
  );
}

export default Article;

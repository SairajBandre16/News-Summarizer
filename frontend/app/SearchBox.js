"use client"
import React, { useState } from 'react';
import axios from 'axios';
import ReadMoreButton from './ReadMoreButton';
import Loading from './Loading';

const SearchBox = () => {
  const [input, setInput] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchNewsByQuery = async (input) => {
    try {
      setSearchResults([]);
      setLoading(true); // Set loading to true before fetching data
      const response = await axios.get(`http://localhost:8080/search`, {
        params: {
          input: input
        }
      });
      const data = response.data;
      const filteredResults = data.filter((article) => article.summary && article.summary.trim() !== '');
      setSearchResults(filteredResults); // Update the search results with the data from the backend
      setLoading(false); // Set loading to false after data is fetched
    } catch (error) {
      console.error('Error fetching news:', error);
      setLoading(false); // Set loading to false if there's an error
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (!input) return;

    fetchNewsByQuery(input);
  };

  return (
    <div>
      <form
        onSubmit={handleSearch}
        className="max-w-6xl mx-auto flex flex-row justify-between items-center px-5"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search keywords"
          className="w-full h-14 rounded-sm placeholder-gray-500 text-gray-500 outline-none flex-1 bg-transparent dark:text-orange-400"
        />
        <button
          type="submit"
          disabled={!input}
          className="text-orange-400 disabled:text-gray-400"
        >
          Search
        </button>
      </form>

      {loading && <Loading/>} {/* Display Loading... while data is being fetched */}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 p-10 gap-10">
        {searchResults.map((article, index) => (
          article.summary && article.summary.trim() !== '' && (
            <article
              key={index}
              className="bg-slate-100 dark:bg-slate-800 flex flex-col rounded-lg shadow-lg hover:scale-105 hover:shadow-xl hover:bg-slate-200 transition-all duration-200 ease-out"
            >
              {article.urlToImage && (
                <img
                  src={article.urlToImage}
                  alt={article.title}
                  className="h-56 w-full object-cover rounded-t-lg shadow-md"
                />
              )}
              <div className="flex-1 flex flex-col">
                <div className="flex-1 flex flex-col p-5">
                  <h2 className="font-bold font-serif line-clamp-2">{article.title}</h2>
                  <section className="mt-2 flex-1">
                    <p className="text-xs ">{article.summary}</p>
                  </section>
                </div>
              </div>
              <ReadMoreButton url={article.url} />
            </article>
          )
        ))}
      </div>
    </div>
  );
};

export default SearchBox;

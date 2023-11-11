"use client"
import Link from 'next/link';
import { useState } from 'react';
import NewsDisplay from './NewsDisplay';

function NavLinks() {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [fetchedNews, setFetchedNews] = useState([]);

  const handleCategoryClick = async (category) => {
    try {
      const response = await fetch(`http://localhost:8080/news_category?category=${category}`);
      const data = await response.json();
      const filteredResults = data.filter((article) => article.summary && article.summary.trim() !== '');
      setFetchedNews(filteredResults); // Update the fetched news data
      setSelectedCategory(category); // Update the selected category
    } catch (error) {
      console.error('Error fetching news:', error);
    }
  };

  return (
    <div>
      <nav className="flex flex-col md:flex-row text-xs md:text-sm gap-4 pb-10 max-w-6xl mx-auto border-b text-center justify-center items-center">
        <Link href="/" onClick={() => handleCategoryClick('business')} className={`navLink ${selectedCategory === 'business' ? 'selectedCategory' : ''}`}>Business</Link>
        <Link href="/" onClick={() => handleCategoryClick('health')} className={`navLink ${selectedCategory === 'health' ? 'selectedCategory' : ''}`}>Health</Link>
        <Link href="/" onClick={() => handleCategoryClick('entertainment')} className={`navLink ${selectedCategory === 'entertainment' ? 'selectedCategory' : ''}`}>Entertainment</Link>
        <Link href="/" onClick={() => handleCategoryClick('sports')} className={`navLink ${selectedCategory === 'sports' ? 'selectedCategory' : ''}`}>Sports</Link>
        <Link href="/" onClick={() => handleCategoryClick('science')} className={`navLink ${selectedCategory === 'science' ? 'selectedCategory' : ''}`}>Science</Link>
        <Link href="/" onClick={() => handleCategoryClick('politics')} className={`navLink ${selectedCategory === 'politics' ? 'selectedCategory' : ''}`}>Politics</Link>
        <Link href="/" onClick={() => handleCategoryClick('technology')} className={`navLink ${selectedCategory === 'technology' ? 'selectedCategory' : ''}`}>Technology</Link>
      </nav>
      {fetchedNews.length > 0 && <NewsDisplay news={fetchedNews} />} {/* Display the fetched news */}
    </div>
  );
}

export default NavLinks;
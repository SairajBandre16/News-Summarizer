"use client"
import React, { useState } from 'react';
import { Bars3Icon } from '@heroicons/react/20/solid';
import Link from 'next/link';
import NavLinks from './NavLinks';
import SearchBox from './SearchBox';
import DarkModeButton from './DarkModeButton';
import NewsDisplay from './NewsDisplay';

function Header() {
  const [fetchedNews, setFetchedNews] = useState([]); // State to hold the fetched news data

  const handleFetchedNews = (news) => {
    setFetchedNews(news); // Function to update the fetched news
  };

  return (
    <header>
      <div className="flex justify-between p-10 items-center">
        <Bars3Icon className="h-8 w-8 cursor-pointer" />
        <Link href="/" prefetch={false}>
          <h1 className="font-serif text-4xl text-center">BlitzFeed</h1>
        </Link>

        <div>
          <DarkModeButton />
        </div>
      </div>

      <NavLinks onCategoryClick={handleFetchedNews} /> {/* Pass the handleFetchedNews function to NavLinks */}
      <SearchBox />
    </header>
  );
}

export default Header;

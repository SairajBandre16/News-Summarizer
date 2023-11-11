import React from 'react';

function ReadMoreButton({ url }) {
  const handleClick = () => {
    window.open(url, '_blank'); 
  };

  return (
    <button
      className="bg-orange-400 h-10 rounded-b-lg dark:text-gray-900 hover:bg-orange-500"
      onClick={handleClick}
    >
      Read full
    </button>
  );
}

export default ReadMoreButton;

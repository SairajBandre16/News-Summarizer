import { fetchedNews} from './NavLinks'

import React from 'react'

function CategoryDisplay() {
  return (
    <div>
      {fetchedNews && fetchedNews.length > 0  && <NewsDisplay news={fetchedNews} />}
    </div>
  )
}

export default CategoryDisplay

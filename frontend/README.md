# BlitzFeed web app

The Next.js frontend for BlitzFeed. See the [main README](../README.md) for the full setup.

## Run it

```bash
npm install
cp .env.example .env.local   # BACKEND_URL points at the Flask API
npm run dev                  # http://localhost:3000
```

Other scripts: `npm run build`, `npm start`, `npm run lint`.

## Layout

- `app/` holds the routes: home, `/[category]`, `/search`, `/saved`, `/brief` (shareable brief), `/about`, plus generated icons and social images.
- `app/api/[...path]/route.js` is the proxy to the Flask API. Only `news`, `search`, `summarize`, `ask`, `compare`, `briefing`, and `health` are forwarded.
- `components/` holds the UI. `ReaderPanel.jsx` is the slide-over reader, `SummaryView.jsx` renders a brief, and `StoryTools.jsx` holds "Ask about this story" and "Compare coverage".
- `lib/server.js` calls the API from server components. `lib/constants.js` holds editions, categories, and the page size.

The production build uses `output: "standalone"`, which the `Dockerfile` copies into a small Node image.

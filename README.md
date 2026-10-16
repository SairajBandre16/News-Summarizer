# BlitzFeed

BlitzFeed turns the day's headlines into short briefs you can read or listen to. Pick a story and you get the key points in a few seconds, without leaving the page. It runs without any API keys. Add a free Groq key for AI-written briefs.

- **Live headlines, no key needed.** Stories come straight from publishers' RSS feeds, including NPR, BBC, The Guardian, The Hindu, and Hindustan Times.
- **Instant briefs.** Each story opens in a reader with a short summary, key points, and topics.
- **Ask this story.** Ask follow-up questions. Answers come only from the article, with a supporting quote.
- **Compare coverage.** When several outlets cover the same event, BlitzFeed groups them into one card and shows what they all report, what only one outlet reports, and where they differ.
- **Today in 60 seconds.** A quick briefing of the top headlines sits at the top of the home page.
- **Listen, save, and share.** Briefs can be read aloud in the browser, saved for later, or shared as a link.
- **US and India editions**, seven categories, search, and a light and dark theme.

## How it works

```
Browser ──► Next.js web app ──► Flask API ──► publishers' RSS feeds (headlines)
             (frontend/)        (backend/) ──► article pages (briefs, answers, comparisons)
                                           ──► Groq or Claude API (optional AI)
                                           ──► NewsAPI (optional, wider search)
```

- **`frontend/`** is a Next.js 16 app (React 19, Tailwind CSS 4). Pages are rendered on the server. Browser calls go through its `/api/*` proxy, so the Flask API never needs to be public and no CORS setup is needed.
- **`backend/`** is a Flask API. It reads the feeds in parallel, groups stories about the same event, caches everything, downloads article pages safely, and extracts the text with `trafilatura`.
- **Without an AI key**, every feature still works. Briefs come from a built-in TextRank summarizer, questions are answered with the article's best-matching passages, and comparisons show how each outlet opens the story.
- **With a Groq key** (free plan) or an Anthropic key, an AI model writes the briefs, the daily briefing, the answers, and the comparisons, and the app labels them as AI. If an AI call fails or the rate budget is used up, the app falls back to the built-in versions.

## Quick start with Docker

You only need Docker.

```bash
git clone https://github.com/SairajBandre16/News-Summarizer.git
cd News-Summarizer
cp backend/.env.example backend/.env    # optional: add GROQ_API_KEY and SECRET_KEY
docker compose up --build
```

Open <http://localhost:3000>. To use another port, run `WEB_PORT=8000 docker compose up --build`.

For AI features, get a free key at <https://console.groq.com/keys> and set `GROQ_API_KEY` in `backend/.env`. Also set `SECRET_KEY` to a long random value (`python -c "import secrets; print(secrets.token_hex(32))"`) so shared brief links keep working across restarts.

## Local development

You need Python 3.11+ and Node.js 20.9+.

**Backend** (runs on <http://127.0.0.1:8080>):

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt      # Windows: .venv\Scripts\pip
cp .env.example .env                               # optional: GROQ_API_KEY, SECRET_KEY
.venv/bin/python app.py
.venv/bin/python -m pytest -q                      # run the tests
```

**Frontend** (runs on <http://localhost:3000>):

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

For a production build, run `npm run build` and then `npm start`. Run the backend with `gunicorn -c gunicorn.conf.py app:app` (gunicorn does not run on Windows).

Every push and pull request runs the backend tests, the frontend lint and build, and both Docker builds on GitHub Actions (`.github/workflows/ci.yml`).

## Configuration

### Backend (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `NEWS_SOURCE` | `rss` | Where headlines come from: `rss` (publishers' feeds, no key) or `newsapi`. |
| `NEWS_API_KEY` | empty | Optional. When set, search covers all of NewsAPI instead of the stories in the current feeds. Required for `NEWS_SOURCE=newsapi`. |
| `AI_PROVIDER` | `auto` | `auto`, `groq`, `anthropic`, or `off`. `auto` uses Anthropic when its key is set, then Groq, then the built-in summarizer. |
| `GROQ_API_KEY` | empty | Turns on AI features through Groq. Get a key at <https://console.groq.com/keys>. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model. `openai/gpt-oss-20b` is faster with the same free limits. |
| `GROQ_MAX_INPUT_CHARS` | `6000` | Article text sent per brief or answer (about 1,000 words). |
| `GROQ_RPM`, `GROQ_TPM`, `GROQ_RPD`, `GROQ_TPD` | `30`, `8000`, `1000`, `200000` | Groq's limits for your plan and model. See [Groq rate limits](#groq-rate-limits). |
| `GROQ_LIMIT_FRACTION` | `0.8` | Share of those limits BlitzFeed plans to use. |
| `GROQ_BRIEFING_SHARE` | `0.3` | Share of the daily budget kept for the daily briefing. |
| `GROQ_BRIEFING_TTL` | `3600` | Seconds to keep an AI briefing before writing a new one. |
| `GROQ_MAX_WAIT` | `10` | Seconds a brief, answer, or comparison may wait for the per-minute limit to clear before it falls back. The briefing never waits. |
| `ANTHROPIC_API_KEY` | empty | Turns on AI features through Claude (paid). |
| `ANTHROPIC_MODEL` | `claude-opus-5-5` | Claude model. |
| `ANTHROPIC_EFFORT` | `low` | Effort level for Claude. |
| `SECRET_KEY` | derived from an API key, else random | Signs article links. Set a long random value. Without any key, a random one is used and shared links break on restart. |
| `DEFAULT_EDITION` | `us` | `us` or `in`. |
| `REDIS_URL` | empty | Shared cache and rate limits. Needed before you run more than one worker. |
| `TRUST_PROXY` | `0` | Number of proxies in front of the API. Docker Compose sets it to `1`. |
| `CORS_ORIGINS` | empty | Only needed if browsers call the API directly instead of through the web app. |
| `SUMMARIZE_RATE_LIMIT` | `15/minute;300/day` | Per-visitor limit on briefs. |
| `ASK_RATE_LIMIT` | `8/minute;80/day` | Per-visitor limit on questions. |
| `COMPARE_RATE_LIMIT` | `6/minute;60/day` | Per-visitor limit on comparisons. |
| `SEARCH_RATE_LIMIT` | `30/minute` | Per-visitor limit on searches. |
| `FEED_TTL` | `900` | Seconds to cache each section's headlines. |
| `COMPARE_TTL` | `21600` | Seconds to cache a comparison. |
| `LOG_LEVEL` | `INFO` | Log level. |

### Frontend (`frontend/.env.local`)

| Variable | Default | Purpose |
|---|---|---|
| `BACKEND_URL` | `http://127.0.0.1:8080` | Where the web server reaches the Flask API. Server-side only. |
| `NEXT_PUBLIC_SITE_URL` | `http://localhost:3000` | Public site URL for share links and social previews. It is built into the browser bundle, so rebuild after you change it. |

## API

All routes are under `/api`.

| Route | Description |
|---|---|
| `GET /health` | Status, editions, categories, news source, and which AI provider and model are on. |
| `GET /news?category=&edition=&offset=&limit=` | Headlines for one category. Stories from several outlets about one event come as one item with a `related` list. |
| `GET /search?q=&sort=&edition=&offset=&limit=` | Search. `sort` is `publishedAt`, `relevancy`, or `popularity`. Uses NewsAPI when `NEWS_API_KEY` is set, otherwise the current feeds. |
| `GET /briefing?edition=` | The "Today in 60 seconds" briefing. |
| `POST /summarize` | Body `{"url", "sig"}`. Writes a brief for one article. |
| `POST /ask` | Body `{"url", "sig", "question"}`. Answers a question (up to 300 characters) from the article's text. |
| `POST /compare` | Body `{"stories": [{"url", "sig"}, ...]}` with 2 to 4 stories. Compares how outlets cover one event. |

Article routes only accept links the API signed itself (the `sig` value in each feed item).

## Groq rate limits

Groq's free plan is small: for `openai/gpt-oss-120b` it allows about 30 requests and 8,000 tokens a minute, and 1,000 requests and 200,000 tokens a day. Check the numbers for your account at <https://console.groq.com/settings/limits> and set the `GROQ_*` limits to match.

BlitzFeed stays under those limits on its own side, so visitors never see Groq errors:

- **Headroom.** It plans against 80% of each limit (`GROQ_LIMIT_FRACTION`).
- **Reserve, then settle.** Each call reserves its estimated tokens before it is sent, then swaps the estimate for the real usage Groq reports.
- **Refuse locally.** A call that would go over a per-minute or per-day limit is not sent, and the visitor gets the built-in version instead. A brief, answer, or comparison waits up to 10 seconds when the per-minute limit is about to clear. The briefing never waits.
- **Follow Groq's headers.** It reads `x-ratelimit-*` on every response, adopts tighter limits than the configured ones, and waits until the reset time when Groq says it is out.
- **Back off, never retry.** A 429 pauses all AI calls for the `retry-after` time. A bad key or model pauses them for an hour. A Groq outage pauses them for 15 seconds.
- **Keep room for the briefing.** 30% of the daily budget is kept for the daily briefing, which is cached for an hour.
- **Cache.** Briefs and answers are cached for 24 hours and comparisons for 6 hours, so each costs one call however many people read it.

Measured on `openai/gpt-oss-120b`, a brief uses about 1,000 to 2,000 tokens, an answer about 850, a comparison about 3,000, and a briefing about 1,700. Briefs, answers, and comparisons share 70% of the daily budget. On the free plan that is roughly 50 to 80 briefs (or a mix with answers and comparisons) and about 25 briefings a day. The budget lives in the API process. With more than one gunicorn process (`WEB_CONCURRENCY`), each process gets an equal slice, and with Groq's per-minute limit that leaves too little for long articles, so keep one process.

## News sources

Feeds are listed in `backend/blitzfeed/feeds.py`, grouped by edition and section. Each section is fetched at most once every 15 minutes, feeds are requested conditionally, and each feed's last good copy is kept for a day if the publisher is down. To add a source, add a `Feed(url, name)` line. Mark it `summarizable=False` if the publisher blocks automated reading, and its stories will link out instead.

Publishers offer RSS feeds so readers can see headlines and follow links to their sites. BlitzFeed shows the headline, a short description, and a link, and always credits the outlet. Check each publisher's feed terms before you run BlitzFeed commercially.

## Security

- The API only fetches article links it signed itself, so it cannot be used to fetch arbitrary URLs or as a free AI proxy.
- The article fetcher allows only http and https on ports 80 and 443. It rejects private, loopback, and cloud metadata addresses, checks every redirect, and stops at 4 MB.
- Questions are answered from the article only. The prompt treats the article and the question as material, not instructions.
- Rate limits use the visitor's address from `X-Forwarded-For`. In production, put the web app behind a reverse proxy or host that sets this header itself, so visitors cannot fake it.

## Limits to know

- Story grouping matches headlines by their words, so now and then it groups two related but different stories. The AI comparison says so when that happens.
- Search without `NEWS_API_KEY` covers the stories currently in the feeds (the last few days). With a key, it covers NewsAPI, whose free plan is for development only, allows 100 requests a day, and returns results about 24 hours old.
- Some stories cannot be summarized: paywalled pages and sites that block automated reading. The reader then links to the original story.
- Claude costs money for each call. Groq's free plan costs nothing but has the tight limits described above.

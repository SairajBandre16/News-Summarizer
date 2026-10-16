import os

bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
# One process with many threads: the work is network-bound, and a single process
# shares the in-memory cache (important for the NewsAPI daily quota). Add workers
# only once REDIS_URL is set so they share a cache.
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "16"))
timeout = 90
graceful_timeout = 20
keepalive = 5
accesslog = "-"
errorlog = "-"

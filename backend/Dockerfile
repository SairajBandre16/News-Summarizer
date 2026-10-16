# BlitzFeed API (Flask + gunicorn)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py gunicorn.conf.py ./
COPY blitzfeed ./blitzfeed

RUN useradd --create-home --uid 10001 blitzfeed
USER blitzfeed

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=4)"]

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]

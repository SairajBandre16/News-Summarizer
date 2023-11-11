from flask import Flask, request, jsonify
import requests
from newspaper import Article
import nltk
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
# Initialize NLTK (you may need to download additional NLTK data)
nltk.download('punkt')

# Define your API key
API_KEY = 'your api key'

# Define a function to fetch news data based on category
def fetch_news(category):
    url = f'https://newsapi.org/v2/top-headlines?country=in&category={category}&apiKey={API_KEY}'
    
    response = requests.get(url)
    data = response.json()
    return data.get('articles', [])

def fetch_all():
    url = f'https://newsapi.org/v2/everything?q=general&apiKey={API_KEY}'
    response = requests.get(url)
    data = response.json()
    return data.get('articles', [])

# Define a function to fetch news data based on search query
def fetchNewsByQuery(input):
    url = f'https://newsapi.org/v2/everything?q={input}&apiKey={API_KEY}'
    response = requests.get(url)
    data = response.json()
    return data.get('articles', [])

# Define a function to summarize an article using newspaper library and NLTK
def summarize_article(url):
    article = Article(url, request_timeout=30)
    article.download()
    article.parse()
    article.nlp()

    return {
        'title': article.title,
        'summary': article.summary,
        'url': article.url,
        'urlToImage': article.top_image,
        'publishedAt': article.publish_date.strftime('%Y-%m-%d %H:%M:%S') if article.publish_date else None
    }

@app.route('/news_category', methods=['GET'])
def news_category():
    max_articles = 15  # Define the maximum number of articles you want to fetch
    category = request.args.get('category')
    articles = fetch_news(category)[:max_articles]  # Fetch a limited number of articles
    summaries = [summarize_article(article['url']) for article in articles]
    return jsonify(summaries)

@app.route('/allnews', methods=['GET'])
def fetch_all_news():
    max_articles = 30  # Define the maximum number of articles you want to fetch

    articles = fetch_all()
    summaries = []
    count = 0

    for article in articles:
        if count >= max_articles:
            break

        summaries.append(summarize_article(article['url']))
        count += 1

    return jsonify(summaries)

@app.route('/search', methods=['GET'])
def search_news_by_query():
    max_articles = 30  # Define the maximum number of articles you want to fetch
    search_query = request.args.get('input')
    articles = fetchNewsByQuery(search_query)[:max_articles]  # Fetch a limited number of articles
    summaries = [summarize_article(article['url']) for article in articles]
    return jsonify(summaries)

if __name__ == '__main__':
    app.run(debug=True, port=8080)
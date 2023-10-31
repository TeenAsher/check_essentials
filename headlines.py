import datetime
import feedparser
import flask
import json
import os
from flask import Flask
from flask import make_response
from flask import render_template
from urllib import parse, request

app = Flask(__name__)

RSS_FEEDS = {
    'cnn': 'http://rss.cnn.com/rss/edition.rss',
    'fox': 'http://feeds.foxnews.com/foxnews/latest',
    'un': 'https://news.un.org/feed/subscribe/ru/news/all/rss.xml',
    'bbc': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'sky': 'https://feeds.skynews.com/feeds/rss/world.xml',
    'nytimes': 'https://rss.nytimes.com/services/xml/rss/nyt/US.xml',
    'asahi': 'https://www.asahi.com/rss/asahi/newsheadlines.rdf'
}

DEFAULTS = {
    'publication': 'cnn',
    'city': 'New York',
    'currency_from': 'EUR',
    'currency_to': 'USD'
}

CURRENCY_URL = os.environ.get("CURRENCY_URL")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

DATE = datetime.date.today()
TODAY = DATE.strftime('%B %d, %Y')

def get_value_with_fallback(key):
    if flask.request.args.get(key):
        return flask.request.args.get(key)
    if flask.request.cookies.get(key):
        return flask.request.cookies.get(key)
    return DEFAULTS[key]

@app.route('/')
def home():
    publication = get_value_with_fallback('publication')
    editor_name = publication.upper()
    articles = get_news(publication)
    city = get_value_with_fallback('city')
    weather = get_weather(city)
    currency_from = get_value_with_fallback('currency_from')
    currency_to = get_value_with_fallback('currency_to')
    rate, currencies = get_rates(currency_from, currency_to)
    response = make_response(
        render_template('home.html', articles=articles, weather=weather,
                        currency_from=currency_from, currency_to=currency_to,
                        rate=rate, currencies=sorted(currencies), date=TODAY, editor_name=editor_name))
    expires = datetime.datetime.now() + datetime.timedelta(days=365)
    response.set_cookie('publication', publication, expires=expires)
    response.set_cookie('city', city, expires=expires)
    response.set_cookie('currency_from', currency_from, expires=expires)
    response.set_cookie('currency_to', currency_to, expires=expires)
    return response

def get_news(query):
    if not query or query.lower() not in RSS_FEEDS:
        publication = DEFAULTS['publication']
    else:
        publication = query.lower()
    feed = feedparser.parse(RSS_FEEDS[publication])
    return feed['entries']

def get_weather(query):
    query = parse.quote(query)
    api_url = f'http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={query}&aqi=no'
    url = api_url.format(query)
    data = request.urlopen(url).read()
    parsed = json.loads(data)
    weather = None
    if parsed.get('current'):
        weather = {
            'description': parsed['current']['condition']['text'],
            'temperature': parsed['current']['temp_c'],
            'city': parsed['location']['name'],
            'country': parsed['location']['country'],
            'image': parsed['current']['condition']['icon']
        }
    return weather

def get_rates(frm, to):
    all_currency = request.urlopen(CURRENCY_URL).read()
    parsed = json.loads(all_currency).get('rates')
    frm_rate = parsed.get(frm.upper())
    to_rate = parsed.get(to.upper())
    return (to_rate / frm_rate, parsed.keys())

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'),404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'),500

if __name__ == '__main__':
    app.run(debug=False)

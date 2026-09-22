import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__) + "/backend")
from scrapers.cagdas_scraper import CagdasScraper
from scrapers.ozgur_scraper import OzgurScraper
from scrapers.ses_scraper import SesScraper
from scrapers.yeni_scraper import YeniScraper
from scrapers.bizimyaka_scraper import BizimyakaScraper
from processing.classifier import classify_news

scrapers = [
    CagdasScraper(),
    OzgurScraper(),
    SesScraper(),
    YeniScraper(),
    BizimyakaScraper(),
]

for scraper in scrapers:
    print(f"--- Testing {scraper.SITE_NAME} ---")
    stubs = scraper.get_article_urls(days=1)
    if not stubs:
        print("No articles found.")
        continue
    url = stubs[0]["url"]
    html = scraper.fetch_page(url)
    if not html:
        print("Failed to fetch.")
        continue
    article = scraper.parse_article(url, html)
    if article:
        cls = classify_news(article["title"], article["content"])
        print(f"URL: {url}")
        print(f"Title: {article['title']}")
        print(f"Date: {article['published_date']}")
        print(f"Content length: {len(article['content'])} chars")
        print(f"Content preview: {article['content'][:200]}...")
        print(f"Classification: {cls}")
    else:
        print("Failed to parse.")

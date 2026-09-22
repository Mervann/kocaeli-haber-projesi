"""Verify date scraping for all sources."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from scrapers.cagdas_scraper import CagdasScraper
from scrapers.ozgur_scraper import OzgurScraper
from scrapers.ses_scraper import SesScraper
from scrapers.yeni_scraper import YeniScraper
from scrapers.bizimyaka_scraper import BizimyakaScraper

scrapers = [
    CagdasScraper(),
    OzgurScraper(),
    SesScraper(),
    YeniScraper(),
    BizimyakaScraper(),
]

for s in scrapers:
    print(f"\n{'='*50}")
    print(f"Testing: {s.SITE_NAME}")
    print(f"{'='*50}")
    try:
        articles = s.scrape(days=1) # Just check last day for speed
        print(f"  Scraped {len(articles)} articles.")
        for a in articles[:3]:
            print(f"  [{a['published_date']}] {a['title'][:60]}...")
    except Exception as e:
        print(f"  ERROR: {e}")

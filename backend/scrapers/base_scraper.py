"""
Base scraper with common functionality for all Kocaeli news sites.
Uses curl_cffi to impersonate Chrome TLS fingerprint, bypassing WAF blocks.
"""

import time
import re
import logging
from datetime import datetime, timedelta, timezone
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
import dateparser
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import REQUEST_TIMEOUT, REQUEST_HEADERS, SCRAPE_DAYS

logger = logging.getLogger("kocaeli")


class BaseScraper(ABC):
    """Abstract base scraper for Kocaeli local news sites."""

    SITE_NAME: str = ""
    BASE_URL: str = ""

    def __init__(self):
        # Use curl_cffi for Chrome TLS fingerprint impersonation
        from curl_cffi.requests import Session
        self.session = Session(impersonate="chrome")
        self.session.headers.update(REQUEST_HEADERS)

    # ── HTTP helpers ──────────────────────────────────────────

    def fetch_page(self, url: str, retries: int = 2) -> str | None:
        """Fetch a page with retry logic. Returns HTML string or None."""
        for attempt in range(retries):
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 403:
                    logger.warning("[%s] 403 Forbidden: %s", self.SITE_NAME, url)
                    return None
                resp.raise_for_status()
                logger.info("[%s] %s OK: %s", self.SITE_NAME, resp.status_code, url[:120])
                return resp.text
            except Exception as e:
                logger.error("[%s] Attempt %d failed for %s: %s", self.SITE_NAME, attempt+1, url, e)
                if attempt < retries - 1:
                    time.sleep(1)
        return None

    # ── Common date parser & utilities ────────────────────────

    @staticmethod
    def extract_google_news_url(rss_url: str) -> str:
        """Extracts the real article URL from a Google News Base64 redirect link."""
        if "news.google.com/rss/articles/" not in rss_url:
            return rss_url
        try:
            import base64
            b64_str = rss_url.split("articles/")[1].split("?")[0]
            b64_str += "==="
            decoded_str = base64.urlsafe_b64decode(b64_str).decode("utf-8", errors="ignore")
            match = re.search(r"https?://[^\s\x00-\x1f\"]+", decoded_str)
            if match:
                return match.group()
        except:
            pass
        return rss_url

    @staticmethod
    def parse_turkish_date(date_str: str) -> datetime | None:
        """
        Parse Turkish date strings robustly using dateparser.
        Returns timezone-aware (UTC+3) datetime, or None if failed.
        """
        if not date_str:
            return None

        # Basic cleans
        date_str = date_str.strip()
        
        # Guard: if string is too short, it's likely not a real date (e.g., "5")
        if len(date_str) < 5:
            return None

        # Guard: must contain at least one digit
        if not any(char.isdigit() for char in date_str):
            return None
            
        try:
            parsed = dateparser.parse(date_str, languages=['tr', 'en'], settings={'TIMEZONE': 'Europe/Istanbul', 'RETURN_AS_TIMEZONE_AWARE': True, 'STRICT_PARSING': False})
            if parsed:
                # Guard: prevent dates from the future (allow 1 day overlap for timezone differences)
                now = datetime.now(timezone(timedelta(hours=3)))
                if parsed > now + timedelta(days=1):
                    return None
                    
                # Ensure it's explicitly +03:00 to match our existing logic
                return parsed.astimezone(timezone(timedelta(hours=3)))
        except Exception as e:
            logger.debug("Date parsing failed for '%s': %s", date_str, e)
            pass

        return None

    def generate_rss_urls(self, base_rss_url: str, days: int) -> list[str]:
        """
        Generate Google News RSS URLs sliced day-by-day to bypass the 100-article
        limit and ensure equal distribution across the requested date window.
        """
        urls = []
        tz = timezone(timedelta(hours=3))
        now = datetime.now(tz)
        for d in range(days):
            target_date = now - timedelta(days=d)
            start_str = target_date.strftime("%Y-%m-%d")
            end_str = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Replace language tag with strict date constraints
            query_suffix = f"+after:{start_str}+before:{end_str}&hl=tr"
            urls.append(base_rss_url.replace("&hl=tr", query_suffix))
        return urls

    # ── Abstract methods for subclasses ───────────────────────

    @abstractmethod
    def get_article_urls(self, days: int = SCRAPE_DAYS) -> list[dict]:
        """
        Get list of article stubs from listing pages.
        Each stub: {"url": str, "title": str (optional)}
        """
        pass

    @abstractmethod
    def parse_article(self, url: str, html: str) -> dict | None:
        """
        Parse a single article page and return:
        {
            "title": str,
            "content": str,
            "published_date": datetime | None,
            "url": str,
            "site_name": str,
        }
        """
        pass

    # ── Main scraping pipeline ────────────────────────────────

    def scrape(self, days: int = SCRAPE_DAYS) -> list[dict]:
        """Full scrape pipeline: get article URLs → fetch & parse each one."""
        from config import MAX_ARTICLES_PER_DAY
        
        logger.info("[%s] Starting scrape for last %d days...", self.SITE_NAME, days)
        articles = []
        stubs = self.get_article_urls(days=days)
        logger.info("[%s] Found %d article links.", self.SITE_NAME, len(stubs))

        daily_counts = {}

        for i, stub in enumerate(stubs):
            url = stub["url"]
            stub_date = stub.get("date")
            
            # 1. Skip network request entirely if stub reveals date and quota is already met
            if stub_date:
                stub_day = stub_date.date()
                if daily_counts.get(stub_day, 0) >= MAX_ARTICLES_PER_DAY:
                    continue

            html = self.fetch_page(url)
            if not html:
                continue

            article = self.parse_article(url, html)
            if not article:
                continue

            # Use stub date as fallback if parsing failed
            if not article.get("published_date") and stub_date:
                article["published_date"] = stub_date

            # Filter by date if we got a date
            if article.get("published_date"):
                now_tr = datetime.now(timezone(timedelta(hours=3)))
                start_of_today = now_tr.replace(hour=0, minute=0, second=0, microsecond=0)
                cutoff = start_of_today - timedelta(days=(days - 1))
                if article["published_date"] < cutoff:
                    continue
                
                # Check daily quota again with the true parsed date
                article_day = article["published_date"].date()
                if daily_counts.get(article_day, 0) >= MAX_ARTICLES_PER_DAY:
                    continue
                
                daily_counts[article_day] = daily_counts.get(article_day, 0) + 1
            else:
                # If absolute no date, categorize under today for balancing purposes
                now_tr = datetime.now(timezone(timedelta(hours=3)))
                today = now_tr.date()
                if daily_counts.get(today, 0) >= MAX_ARTICLES_PER_DAY:
                    continue
                daily_counts[today] = daily_counts.get(today, 0) + 1

            articles.append(article)
            # Be polite
            time.sleep(0.3)

        logger.info("[%s] Scraped %d articles.", self.SITE_NAME, len(articles))
        return articles

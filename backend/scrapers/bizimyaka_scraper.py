"""Refined Bizim Yaka scraper with better date extraction."""
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

class BizimyakaScraper(BaseScraper):
    SITE_NAME = "Bizim Yaka"
    BASE_URL = "https://www.bizimyaka.com"

    LISTING_URLS = [
        "https://www.bizimyaka.com/kocaeli-asayis-haberleri",
        "https://www.bizimyaka.com/kocaeli-gundem-haberleri",
        "https://www.bizimyaka.com/kocaeli-yasam-haberleri",
        "https://www.bizimyaka.com/kocaeli-siyaset-haberleri",
        "https://www.bizimyaka.com/kocaeli-guncel-haberleri",
    ]

    def get_article_urls(self, days=3) -> list[dict]:
        stubs = []
        seen = set()
        for listing_url in self.LISTING_URLS:
            html = self.fetch_page(listing_url)
            if not html: continue
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/haber/" in href:
                    url = href if href.startswith("http") else self.BASE_URL + href
                    if url not in seen:
                        seen.add(url)
                        stubs.append({"url": url, "title": a.get_text(strip=True)})
        return stubs

    def parse_article(self, url: str, html: str) -> dict | None:
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else None
        if not title:
            og = soup.find("meta", property="og:title")
            title = og["content"] if og else None
        if not title: return None

        # Content area
        article_body = (
            soup.find("div", class_=re.compile(r"article[-_]?body|news[-_]?content|detail[-_]?content", re.I))
            or soup.find("article")
        )
        
        content = ""
        if article_body:
            for unwanted in article_body.find_all(["script", "style", "aside", "nav", "iframe"]):
                unwanted.decompose()
            content = article_body.get_text(separator="\n", strip=True)
        else:
            og_desc = soup.find("meta", property="og:description")
            if og_desc: content = og_desc.get("content", "")

        # Date extraction
        date = None
        
        # 1. Search for time/date tags specifically NEAR the title or inside the article body
        # Many sites have a class like "date" or "tarih"
        date_el = (
            soup.find(class_=re.compile(r"date|tarih|time", re.I))
            or soup.find(id=re.compile(r"date|tarih|time", re.I))
        )
        if date_el:
            # Check if it has a datetime attribute
            if date_el.name == "time" and date_el.get("datetime"):
                date = self.parse_turkish_date(date_el["datetime"])
            else:
                # Try to parse the text
                text = date_el.get_text(strip=True)
                # Filter out garbage (e.g. "Bugün", "Dün" are fine, but long sentences are not)
                if text and len(text) < 50:
                    date = self.parse_turkish_date(text)

        # 2. Meta tags
        if not date:
            for meta_name in ["article:published_time", "article:published", "datePublished", "pubdate", "publish-date"]:
                m = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
                if m:
                    date = self.parse_turkish_date(m.get("content", ""))
                    if date: break

        # 3. LD+JSON
        if not date:
            import json
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and "datePublished" in data:
                        date = self.parse_turkish_date(data["datePublished"])
                        if date: break
                except: pass

        return {
            "title": title,
            "content": content,
            "published_date": date,
            "url": url,
            "site_name": self.SITE_NAME,
        }

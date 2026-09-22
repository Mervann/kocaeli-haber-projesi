"""Scraper for cagdaskocaeli.com.tr — Uses Google News RSS to discover articles
since the site is behind Cloudflare WAF that blocks all programmatic access.
Content is extracted from article meta tags via Google's cached version."""

import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

from .base_scraper import BaseScraper


class CagdasScraper(BaseScraper):
    SITE_NAME = "Çağdaş Kocaeli"
    BASE_URL = "https://www.cagdaskocaeli.com.tr"

    # Google News RSS for this specific site
    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q=site:cagdaskocaeli.com.tr+Kocaeli&hl=tr&gl=TR&ceid=TR:tr"

    def get_article_urls(self, days=3) -> list[dict]:
        stubs = []
        seen = set()

        # 1. Try Google News RSS to discover articles
        rss_urls = self.generate_rss_urls(self.GOOGLE_NEWS_RSS, days)
        for rss_url in rss_urls:
            html = self.fetch_page(rss_url)
            if html:
                soup = BeautifulSoup(html, "lxml-xml")
                for item in soup.find_all("item"):
                    link_tag = item.find("link")
                    title_tag = item.find("title")
                    pub_date = item.find("pubDate")

                    if link_tag:
                        url = link_tag.get_text(strip=True)
                        if not url:
                            url = link_tag.next_sibling
                            if url:
                                url = url.strip()

                        # Google News wraps URLs; extract the real URL
                        url = self.extract_google_news_url(url)
                        if url and "cagdaskocaeli.com.tr" in url and url not in seen:
                            seen.add(url)
                            title = title_tag.get_text(strip=True) if title_tag else ""
                            
                            # Extract date from RSS if available
                            date = None
                            if pub_date:
                                date = self.parse_turkish_date(pub_date.get_text(strip=True))
                                
                            stubs.append({"url": url, "title": title, "date": date})

        # 2. Fallback: try direct access (may work if Cloudflare is temporarily relaxed)
        if len(stubs) == 0:
            for listing_url in [
                f"{self.BASE_URL}/kocaeli-asayis-haberleri",
                f"{self.BASE_URL}/kocaeli-gundem-haberleri",
                f"{self.BASE_URL}/kocaeli-guncel-haberleri",
            ]:
                page_html = self.fetch_page(listing_url)
                if page_html and "/haber/" in page_html:
                    soup = BeautifulSoup(page_html, "lxml")
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

        # Title
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else None
        if not title:
            og = soup.find("meta", property="og:title")
            title = og["content"] if og else None
        if not title:
            return None

        # Content
        content = ""
        article_body = (
            soup.find("div", class_=re.compile(r"article[-_]?body|news[-_]?content|detail[-_]?content|haber[-_]?detay", re.I))
            or soup.find("div", class_=re.compile(r"content[-_]?text|news[-_]?text", re.I))
            or soup.find("article")
        )

        if article_body:
            for unwanted in article_body.find_all(["script", "style", "aside", "nav", "iframe"]):
                unwanted.decompose()
            content = article_body.get_text(separator="\n", strip=True)
        else:
            og_desc = soup.find("meta", property="og:description")
            if og_desc:
                content = og_desc.get("content", "")

        # If content is still empty or too short (Cloudflare block page), use og:description
        if len(content) < 100:
            og_desc = soup.find("meta", property="og:description")
            if og_desc:
                content = og_desc.get("content", "")

        # Date
        date = None

        # 1. Tarih/date class'lı elementler (Bizim Yaka pattern)
        date_el = (
            soup.find(class_=re.compile(r"date|tarih|time", re.I))
            or soup.find(id=re.compile(r"date|tarih|time", re.I))
        )
        if date_el:
            if date_el.name == "time" and date_el.get("datetime"):
                date = self.parse_turkish_date(date_el["datetime"])
            else:
                text = date_el.get_text(strip=True)
                if text and len(text) < 50:
                    date = self.parse_turkish_date(text)

        # 2. <time> tag
        if not date:
            time_tag = soup.find("time")
            if time_tag:
                date = self.parse_turkish_date(time_tag.get("datetime", "") or time_tag.get_text())

        # 3. Meta tags — birden fazla property ismi dene
        if not date:
            for meta_name in ["article:published_time", "article:published", "datePublished", "pubdate", "publish-date"]:
                m = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
                if m:
                    date = self.parse_turkish_date(m.get("content", ""))
                    if date:
                        break

        # 4. LD+JSON datePublished
        if not date:
            import json
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and "datePublished" in data:
                        date = self.parse_turkish_date(data["datePublished"])
                        if date:
                            break
                except:
                    pass

        # 5. Tüm text node'larda tarih regex araması (geniş — saat olmadan da eşleşir)
        if not date:
            date_pattern = re.compile(r"\d{1,2}\s+\w+\s+\d{4}")
            for text_node in soup.find_all(string=date_pattern):
                text = text_node.strip()
                if text and len(text) < 60:
                    parsed = self.parse_turkish_date(text)
                    if parsed:
                        date = parsed
                        break

        # 6. Belirli element tiplerinde geniş arama
        if not date:
            for el in soup.find_all(["span", "div", "small", "em", "p", "li", "time"]):
                text = el.get_text(strip=True)
                if text and len(text) < 60 and re.search(r"\d{1,2}\s+\w+\s+\d{4}", text):
                    parsed = self.parse_turkish_date(text)
                    if parsed:
                        date = parsed
                        break

        return {
            "title": title,
            "content": content,
            "published_date": date,
            "url": url,
            "site_name": self.SITE_NAME,
        }

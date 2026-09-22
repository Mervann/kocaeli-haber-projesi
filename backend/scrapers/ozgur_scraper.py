"""Scraper for ozgurkocaeli.com.tr — uses multiple RSS feeds since main pages return 403."""

import re
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper


class OzgurScraper(BaseScraper):
    SITE_NAME = "Özgür Kocaeli"
    BASE_URL = "https://www.ozgurkocaeli.com.tr"

    # Multiple Google News RSS queries to maximize article discovery
    # Site is 403 for direct access, so RSS is the primary source
    GOOGLE_RSS_QUERIES = [
        "https://news.google.com/rss/search?q=site:ozgurkocaeli.com.tr&hl=tr&gl=TR&ceid=TR:tr",
        "https://news.google.com/rss/search?q=site:ozgurkocaeli.com.tr+haber&hl=tr&gl=TR&ceid=TR:tr",
    ]

    # Site's own RSS feed (may work even when HTML pages return 403)
    SITE_RSS_URLS = [
        "https://www.ozgurkocaeli.com.tr/rss",
        "https://www.ozgurkocaeli.com.tr/feed",
        "https://www.ozgurkocaeli.com.tr/rss.xml",
    ]

    def fetch_page(self, url: str, retries: int = 2) -> str | None:
        """Direct fetch first; if blocked by Cloudflare, retry via Google Cache."""
        import logging
        logger = logging.getLogger("kocaeli")

        # 1. Try direct fetch
        html = super().fetch_page(url, retries=retries)
        
        # 2. Cloudflare Engel Kontrolü (Sayfa geldi ama içinde koruma mesajı mı var?)
        is_blocked = False
        if html:
            # Cloudflare'in tipik uyarı kelimelerini arıyoruz
            cf_keywords = ["Just a moment...", "cf-browser-verification", "DDoS protection by Cloudflare", "Lütfen bekleyin, bağlantınız"]
            if any(keyword in html for keyword in cf_keywords) or len(html) < 1000:
                is_blocked = True

        # Eğer sayfa geldiyse ve bloklanmamışsa, asıl HTML'i döndür
        if html and not is_blocked:
            return html

        # 3. 403, başarısız veya Cloudflare engeli → Google Cache üzerinden dene
        if "news.google.com" in url or "webcache.googleusercontent.com" in url:
            return None  # RSS ve cache URL'leri için cache deneme

        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
        logger.info("[%s] Blocked or 403, trying Google Cache: %s", self.SITE_NAME, url[:80])
        
        try:
            resp = self.session.get(cache_url, timeout=15)
            if resp.status_code == 200:
                logger.info("[%s] Google Cache OK: %s", self.SITE_NAME, url[:80])
                return resp.text
            else:
                logger.warning("[%s] Google Cache %s: %s", self.SITE_NAME, resp.status_code, url[:80])
        except Exception as e:
            logger.error("[%s] Google Cache failed: %s", self.SITE_NAME, e)
            
        return None

    def get_article_urls(self, days=3) -> list[dict]:
        stubs = []
        seen = set()

        # 1. Google News RSS — multiple queries, day-by-day sliced
        for base_rss in self.GOOGLE_RSS_QUERIES:
            rss_urls = self.generate_rss_urls(base_rss, days)
            for rss_url in rss_urls:
                html = self.fetch_page(rss_url)
                if html:
                    soup = BeautifulSoup(html, "lxml-xml")
                    for item in soup.find_all("item"):
                        link_tag = item.find("link")
                        title_tag = item.find("title")
                        if link_tag:
                            url = link_tag.get_text(strip=True)
                            if not url:
                                url = link_tag.next_sibling
                                if url:
                                    url = url.strip()

                            url = self.extract_google_news_url(url)
                            if url and "ozgurkocaeli.com.tr" in url and url not in seen:
                                seen.add(url)
                                title = title_tag.get_text(strip=True) if title_tag else ""

                                date = None
                                pub_date = item.find("pubDate")
                                if pub_date:
                                    date = self.parse_turkish_date(pub_date.get_text(strip=True))

                                stubs.append({"url": url, "title": title, "date": date})

        # 2. Site's own RSS feed (may bypass 403 since it's XML, not HTML)
        for rss_url in self.SITE_RSS_URLS:
            html = self.fetch_page(rss_url)
            if html and "<item" in html.lower():
                soup = BeautifulSoup(html, "lxml-xml")
                for item in soup.find_all("item"):
                    link_tag = item.find("link")
                    title_tag = item.find("title")
                    if link_tag:
                        url = link_tag.get_text(strip=True)
                        if not url:
                            url = link_tag.next_sibling
                            if url:
                                url = url.strip()
                        if url and url.startswith("http") and url not in seen:
                            seen.add(url)
                            title = title_tag.get_text(strip=True) if title_tag else ""
                            date = None
                            pub_date = item.find("pubDate")
                            if pub_date:
                                date = self.parse_turkish_date(pub_date.get_text(strip=True))
                            stubs.append({"url": url, "title": title, "date": date})

        # 3. Direct listing pages (may fail with 403, but worth trying)
        for listing_url in [
            self.BASE_URL,
            f"{self.BASE_URL}/kocaeli-asayis-haberleri",
            f"{self.BASE_URL}/kocaeli-gundem-haberleri",
            f"{self.BASE_URL}/kocaeli-guncel-haberleri",
        ]:
            page_html = self.fetch_page(listing_url)
            if page_html:
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

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else None
        if not title:
            og = soup.find("meta", property="og:title")
            title = og["content"] if og else None
        if not title:
            return None

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

        if len(content) < 100:
            og_desc = soup.find("meta", property="og:description")
            if og_desc:
                content = og_desc.get("content", "")

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

        # 3. Meta tags — birden fazla property ismi dene (Bizim Yaka pattern)
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

        # 5. Tüm text node'larda tarih regex araması (Çağdaş pattern)
        if not date:
            date_pattern = re.compile(r"\d{1,2}\s+\w+\s+\d{4}")
            for text_node in soup.find_all(string=date_pattern):
                text = text_node.strip()
                if text and len(text) < 60:
                    parsed = self.parse_turkish_date(text)
                    if parsed:
                        date = parsed
                        break

        # 6. Belirli element tiplerinde geniş arama (Yeni Kocaeli pattern)
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

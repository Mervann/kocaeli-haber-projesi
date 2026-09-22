"""Scraper for yenikocaeli.com — Uses Google News RSS as primary source
and www.yenikocaeli.com (with www) for direct access.
The site has intermittent connectivity issues."""

import re
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper


class YeniScraper(BaseScraper):
    SITE_NAME = "Yeni Kocaeli"
    BASE_URL = "https://www.yenikocaeli.com"

    # Google News RSS as primary article discovery
    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q=site:yenikocaeli.com+Kocaeli&hl=tr&gl=TR&ceid=TR:tr"

    def get_article_urls(self, days=3) -> list[dict]:
        stubs = []
        seen = set()

        # 1. Primary: Google News RSS
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
                        if url and "yenikocaeli.com" in url and url not in seen:
                            seen.add(url)
                            title = title_tag.get_text(strip=True) if title_tag else ""
                            
                            # Extract date from RSS if available
                            date = None
                            if pub_date:
                                date = self.parse_turkish_date(pub_date.get_text(strip=True))
                                
                            stubs.append({"url": url, "title": title, "date": date})

        # 2. Main page link discovery (since categories return 404)

        # 3. Main page
        html = self.fetch_page(self.BASE_URL)
        if html:
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # URLs look like /dipsiz-gole-ziyaretci-ilgisi-havadan-goruntulendi/193222.html
                if re.search(r'/\d+\.html', href):
                    if href.startswith("http"):
                        url = href
                    elif href.startswith("/"):
                        url = self.BASE_URL + href
                    else:
                        url = self.BASE_URL + "/" + href
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
            soup.find("div", class_=re.compile(r"article[-_]?body|news[-_]?content|detail[-_]?content|haber", re.I))
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

        # Date parsing — try multiple approaches
        date = None
        
        # 1. <time> tag
        time_tag = soup.find("time")
        if time_tag:
            date = self.parse_turkish_date(time_tag.get("datetime", "") or time_tag.get_text())

        # 2. meta article:published_time
        if not date:
            meta_date = soup.find("meta", property="article:published_time")
            if meta_date:
                date = self.parse_turkish_date(meta_date.get("content", ""))

        # 3. LD+JSON
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

        # 4. Look for <div class="date">
        if not date:
            date_div = soup.find("div", class_="date")
            if date_div:
                text = date_div.get_text(strip=True)
                # Text looks like: ", 01 April 2026"
                if text:
                    text_clean = text.lstrip(" ,-").strip()
                    date = self.parse_turkish_date(text_clean)

        # 5. Look for date-like text in spans/divs near the title
        if not date:
            # Turkish date: "31 Mart 2026" or "31 Mart 2026 - 14:30"
            date_pattern = re.compile(r"\d{1,2}\s+\w+\s+\d{4}")
            for el in soup.find_all(["span", "div", "small", "em", "p", "li"]):
                text = el.get_text(strip=True)
                if text and len(text) < 60 and date_pattern.search(text):
                    parsed = self.parse_turkish_date(text)
                    if parsed:
                        date = parsed
                        break


        # 5. URL-based date extraction (e.g., /haber/27722343/...)
        # Some CMS embed date info in article ID ranges — not reliable, skip

        return {
            "title": title,
            "content": content,
            "published_date": date,
            "url": url,
            "site_name": self.SITE_NAME,
        }

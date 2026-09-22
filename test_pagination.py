import requests
from bs4 import BeautifulSoup
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from config import REQUEST_HEADERS

urls = [
    "https://www.cagdaskocaeli.com.tr/kocaeli-asayis-haberleri",
    "https://www.cagdaskocaeli.com.tr/kocaeli-asayis-haberleri?page=2",
    "https://yenikocaeli.com/kategori/guncel?page=2",
    "https://www.ozgurkocaeli.com.tr/kocaeli-asayis-haberleri?page=2",
    "https://www.seskocaeli.com/kocaeli-asayis-haberleri?page=2",
    "https://www.bizimyaka.com/asayis-haberleri?page=2"
]

session = requests.Session()
session.headers.update(REQUEST_HEADERS)

for url in urls:
    resp = session.get(url, timeout=10)
    print(f"{url} -> {resp.status_code}")
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "lxml")
        links = [a["href"] for a in soup.find_all("a", href=True) if "/haber/" in a["href"]]
        print(f"  Found {len(links)} links")

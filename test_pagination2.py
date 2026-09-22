import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0"}
test_urls = [
    "https://www.cagdaskocaeli.com.tr/kocaeli-asayis-haberleri/sayfa/2",
    "https://www.cagdaskocaeli.com.tr/kocaeli-asayis-haberleri?p=2",
    "https://www.cagdaskocaeli.com.tr/kocaeli-asayis-haberleri?pg=2",
    "https://www.ozgurkocaeli.com.tr/kocaeli-asayis-haberleri/sayfa/2",
]

for url in test_urls:
    r = requests.get(url, headers=headers)
    print(f"{url} -> {r.status_code}")

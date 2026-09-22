import cloudscraper

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

urls = [
    "https://www.cagdaskocaeli.com.tr/kocaeli-asayis-haberleri",
    "https://www.ozgurkocaeli.com.tr/kocaeli-asayis-haberleri",
]

for url in urls:
    try:
        r = scraper.get(url, timeout=10)
        print(f"{url} -> {r.status_code}")
    except Exception as e:
        print(f"{url} -> Error: {e}")

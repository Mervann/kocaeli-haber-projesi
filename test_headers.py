import requests

urls = [
    "https://www.cagdaskocaeli.com.tr/kocaeli-asayis-haberleri",
    "https://yenikocaeli.com/kategori/guncel"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1"
}

for url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f"{url} -> {r.status_code}")
    except Exception as e:
        print(f"{url} -> {e}")

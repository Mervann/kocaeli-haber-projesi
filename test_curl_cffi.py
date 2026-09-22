from curl_cffi import requests

urls = [
    "https://www.cagdaskocaeli.com.tr/kocaeli-asayis-haberleri",
    "https://www.ozgurkocaeli.com.tr/kocaeli-asayis-haberleri",
]

for url in urls:
    try:
        r = requests.get(url, impersonate="chrome110", timeout=10)
        print(f"{url} -> {r.status_code}")
    except Exception as e:
        print(f"{url} -> Error: {e}")

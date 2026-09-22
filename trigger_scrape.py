import urllib.request
import json

url = 'http://127.0.0.1:5000/api/scrape'
data = json.dumps({"days": 3}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(f"Error: {e}")

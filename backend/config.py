import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "kocaeli_news")

# Google Maps
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GOOGLE_GEOCODING_API_KEY = os.getenv("GOOGLE_GEOCODING_API_KEY", GOOGLE_MAPS_API_KEY)

# Scraping settings
SCRAPE_DAYS = 3  # Default: fetch news from last 3 days (per project requirements)
MAX_ARTICLES_PER_DAY = 15  # Limit per scraper per day to ensure balanced distribution
REQUEST_TIMEOUT = 15  # seconds
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

# News types with priority order
NEWS_TYPES = [
    "Trafik Kazası",
    "Yangın",
    "Elektrik Kesintisi",
    "Hırsızlık",
    "Kültürel Etkinlikler",
    "Genel",
]

# Kocaeli districts
KOCAELI_DISTRICTS = [
    "İzmit", "Gebze", "Darıca", "Derince", "Çayırova",
    "Dilovası", "Gölcük", "Kandıra", "Karamürsel", "Kartepe",
    "Körfez", "Başiskele",
]

# Duplicate detection threshold
SIMILARITY_THRESHOLD = 0.70

# Geocoding
GEOCODE_USER_AGENT = "KocaeliNewsMonitor/1.0"

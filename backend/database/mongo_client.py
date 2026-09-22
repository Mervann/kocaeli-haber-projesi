from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import MONGODB_URI, MONGODB_DB


class MongoDBClient:
    """MongoDB operations for news storage and retrieval."""

    def __init__(self):
        self._client = None
        self._db = None
        self._news = None
        self._geocode_cache = None

    def _connect(self):
        """Lazy connection – called on first DB operation."""
        if self._client is None:
            self._client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            self._db = self._client[MONGODB_DB]
            self._news = self._db["news"]
            self._geocode_cache = self._db["geocode_cache"]
            self._ensure_indexes()

    @property
    def news(self):
        self._connect()
        return self._news

    @property
    def geocode_cache(self):
        self._connect()
        return self._geocode_cache

    def _ensure_indexes(self):
        """Create indexes for efficient queries."""
        self._news.create_index([("published_date", ASCENDING)])
        self._news.create_index([("news_type", ASCENDING)])
        self._news.create_index([("district", ASCENDING)])
        self._news.create_index([("sources.url", ASCENDING)])
        self._geocode_cache.create_index([("query", ASCENDING)], unique=True)

    # ── News CRUD ──────────────────────────────────────────────

    def insert_news(self, news_data: dict) -> str:
        """Insert a new news document. Returns inserted_id."""
        news_data["created_at"] = datetime.now(timezone.utc)
        result = self.news.insert_one(news_data)
        return str(result.inserted_id)

    def url_exists(self, url: str) -> bool:
        """Check if a news URL already exists in any source."""
        return self.news.find_one({"sources.url": url}) is not None

    def add_source_to_news(self, news_id, source: dict):
        """Add a new source to an existing news document."""
        from bson import ObjectId
        self.news.update_one(
            {"_id": ObjectId(news_id)},
            {"$addToSet": {"sources": source}}
        )

    def get_all_news(self, filters: dict = None) -> list:
        """Retrieve news with optional filters."""
        query = {}
        if filters:
            if filters.get("news_type"):
                query["news_type"] = filters["news_type"]
            if filters.get("district"):
                query["district"] = filters["district"]
            if filters.get("date_from"):
                query.setdefault("published_date", {})["$gte"] = filters["date_from"]
            if filters.get("date_to"):
                query.setdefault("published_date", {})["$lte"] = filters["date_to"]

        cursor = self.news.find(query).sort("published_date", -1)
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            # Convert datetime for JSON serialisation and append Z so JS interprets as UTC
            if isinstance(doc.get("published_date"), datetime):
                doc["published_date"] = doc["published_date"].isoformat() + "Z"
            if isinstance(doc.get("created_at"), datetime):
                doc["created_at"] = doc["created_at"].isoformat() + "Z"
            results.append(doc)
        return results

    def get_all_embeddings(self) -> list:
        """Return id, title, and embedding for every news item that has an embedding."""
        cursor = self.news.find(
            {"embedding": {"$exists": True}},
            {"_id": 1, "title": 1, "embedding": 1}
        )
        return list(cursor)

    def get_distinct_districts(self) -> list:
        """Return list of unique districts."""
        return sorted(self.news.distinct("district"))

    def delete_old_news(self, days: int = 3) -> int:
        """Delete news older than the specified number of days (calendar days)."""
        from datetime import timedelta
        # Determine the start of the day in Turkey time (UTC+3)
        tz = timezone(timedelta(hours=3))
        now_tr = datetime.now(tz)
        start_of_today = now_tr.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = start_of_today - timedelta(days=(days - 1))
        
        result = self.news.delete_many({"published_date": {"$lt": cutoff_date}})
        return result.deleted_count

    def clear_all_news(self):
        """Delete all news (useful for dev/testing)."""
        self.news.delete_many({})

    # ── Geocode Cache ──────────────────────────────────────────

    def get_cached_geocode(self, query: str):
        """Look up cached geocoding result."""
        return self.geocode_cache.find_one({"query": query})

    def cache_geocode(self, query: str, lat: float, lon: float):
        """Store geocoding result in cache."""
        self.geocode_cache.update_one(
            {"query": query},
            {"$set": {
                "latitude": lat,
                "longitude": lon,
                "cached_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )


# Singleton instance
db = MongoDBClient()

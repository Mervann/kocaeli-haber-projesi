"""
Flask application – Kocaeli Urban News Monitoring API.

Endpoints:
  GET  /api/news          – list news (with filters)
  POST /api/scrape         – trigger scraping pipeline
  GET  /api/news/types     – available news types
  GET  /api/news/districts – available districts
  GET  /                   – serve frontend
"""

import os
import sys
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(__file__))

# ── Logging Setup ────────────────────────────────────────────
# Named logger'a doğrudan handler ekliyoruz (basicConfig Flask tarafından override edilebilir)
logger = logging.getLogger("kocaeli")
logger.setLevel(logging.INFO)
logger.propagate = False  # Root logger'a bağımlı olma

_log_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

_sh = logging.StreamHandler(sys.stderr)
_sh.setFormatter(_log_fmt)
logger.addHandler(_sh)

_fh = logging.FileHandler(
    os.path.join(os.path.dirname(__file__), "scrapers.log"),
    encoding="utf-8",
)
_fh.setFormatter(_log_fmt)
logger.addHandler(_fh)
from config import NEWS_TYPES, GOOGLE_MAPS_API_KEY
from database.mongo_client import db
from processing.cleaner import clean_text
from processing.classifier import classify_news
from processing.location_extractor import extract_location
from processing.geocoder import geocode
from processing.deduplicator import compute_embedding, find_duplicate

# Import scrapers
from scrapers.cagdas_scraper import CagdasScraper
from scrapers.ozgur_scraper import OzgurScraper
from scrapers.ses_scraper import SesScraper
from scrapers.yeni_scraper import YeniScraper
from scrapers.bizimyaka_scraper import BizimyakaScraper

# ── Flask App ─────────────────────────────────────────────────

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend"),
    static_url_path="",
)
CORS(app)

# Scraping status
_scrape_status = {"running": False, "message": "", "count": 0}

ALL_SCRAPERS = [
    CagdasScraper(),
    OzgurScraper(),
    SesScraper(),
    YeniScraper(),
    BizimyakaScraper(),
]

# ── Routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/news")
def get_news():
    """Get news with optional filters."""
    try:
        filters = {}
        if request.args.get("news_type"):
            filters["news_type"] = request.args["news_type"]
        if request.args.get("district"):
            filters["district"] = request.args["district"]
        if request.args.get("date_from"):
            try:
                filters["date_from"] = datetime.fromisoformat(request.args["date_from"])
            except ValueError:
                pass
        if request.args.get("date_to"):
            try:
                filters["date_to"] = datetime.fromisoformat(request.args["date_to"])
            except ValueError:
                pass

        news = db.get_all_news(filters if filters else None)
        return jsonify({"news": news, "count": len(news)})
    except Exception as e:
        logger.error("[API] /api/news: %s", e)
        return jsonify({"news": [], "count": 0})


@app.route("/api/news/types")
def get_news_types():
    return jsonify({"types": NEWS_TYPES})


@app.route("/api/news/districts")
def get_districts():
    try:
        return jsonify({"districts": db.get_distinct_districts()})
    except Exception as e:
        logger.error("[API] /api/news/districts: %s", e)
        return jsonify({"districts": []})


@app.route("/api/scrape", methods=["POST"])
def trigger_scrape():
    """Trigger scraping pipeline in background."""
    global _scrape_status

    if _scrape_status["running"]:
        return jsonify({"status": "already_running", "message": "Scraping is already in progress."}), 409

    days = request.json.get("days", 3) if request.is_json else 3

    def run_scrape():
        global _scrape_status
        _scrape_status = {"running": True, "message": "Scraping started...", "count": 0}
        total_saved = 0

        try:
            # Auto-cleanup old data: keep only last 3 days
            deleted_count = db.delete_old_news(days=3)
            logger.info("[Cleanup] Deleted %d news articles older than 3 days.", deleted_count)

            # Run all scrapers in parallel
            start_time = time.time()
            all_names = [s.SITE_NAME for s in ALL_SCRAPERS]
            _scrape_status["message"] = f"Paralel çalışıyor: {', '.join(all_names)}"
            logger.info("[Scrape] 5 scraper paralel başlatıldı: %s", ', '.join(all_names))

            def scrape_one(scraper):
                try:
                    result = scraper.SITE_NAME, scraper.scrape(days=days)
                    logger.info("[Done] %s: %d haber bulundu.", scraper.SITE_NAME, len(result[1]))
                    return result
                except Exception as e:
                    logger.error("[Error] %s: %s", scraper.SITE_NAME, e)
                    return scraper.SITE_NAME, []

            completed = []
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {pool.submit(scrape_one, s): s for s in ALL_SCRAPERS}
                for future in as_completed(futures):
                    site_name, articles = future.result()
                    completed.append(site_name)
                    remaining = [n for n in all_names if n not in completed]
                    if remaining:
                        _scrape_status["message"] = f"{site_name} tamamlandı. Devam eden: {', '.join(remaining)}"
                    else:
                        _scrape_status["message"] = "Tüm scraperlar tamamlandı, haberler kaydediliyor..."
                    for article in articles:
                        try:
                            saved = process_and_save(article)
                            if saved:
                                total_saved += 1
                        except Exception as e:
                            logger.error("[Error] Processing article: %s", e)
                            continue

            elapsed = time.time() - start_time
            _scrape_status = {
                "running": False,
                "message": f"Scraping complete. {total_saved} new articles saved in {elapsed:.1f}s.",
                "count": total_saved,
            }
            logger.info("[Done] %d articles saved in %.1fs.", total_saved, elapsed)
        except Exception as e:
            _scrape_status = {"running": False, "message": f"Error: {str(e)}", "count": total_saved}

    thread = threading.Thread(target=run_scrape, daemon=True)
    thread.start()

    return jsonify({"status": "started", "message": "Scraping started in background."})


@app.route("/api/scrape/status")
def scrape_status():
    return jsonify(_scrape_status)


@app.route("/api/config")
def get_config():
    """Return frontend config (e.g., maps API key)."""
    return jsonify({"google_maps_api_key": GOOGLE_MAPS_API_KEY})


@app.route("/api/sources")
def get_sources():
    """Return all news grouped by source site with full details."""
    try:
        all_news = db.get_all_news()
        sources = {}
        for n in all_news:
            for src in n.get("sources", []):
                site = src.get("site_name", "Bilinmiyor")
                if site not in sources:
                    sources[site] = {"site_name": site, "news": [], "count": 0}
                sources[site]["news"].append({
                    "title": n.get("title", ""),
                    "news_type": n.get("news_type", ""),
                    "district": n.get("district", ""),
                    "published_date": n.get("published_date"),
                    "url": src.get("url", "#"),
                    "location_text": n.get("location_text", ""),
                })
                sources[site]["count"] += 1
        return jsonify({"sources": list(sources.values())})
    except Exception as e:
        logger.error("[API] /api/sources: %s", e)
        return jsonify({"sources": []})


@app.route("/kaynak-detay")
def source_detail_page():
    """Serve source details page."""
    return send_from_directory(app.static_folder, "kaynak-detay.html")


# ── Processing Pipeline ──────────────────────────────────────

def process_and_save(article: dict) -> bool:
    """
    Process a raw article through the full pipeline:
    1. Check URL duplicate
    2. Clean text
    3. Classify
    4. Extract location
    5. Geocode
    6. Embedding-based duplicate check
    7. Save to MongoDB
    """
    url = article.get("url", "")
    site_name = article.get("site_name", "")

    # 1. URL duplicate check
    if db.url_exists(url):
        logger.debug("[Skip] URL zaten var: %s", url)
        return False

    # 2. Clean text
    title = article.get("title", "")
    raw_content = article.get("content", "")
    content = clean_text(raw_content)

    if not title or not content or len(content) < 20:
        logger.warning("[Skip] İçerik yetersiz: %s", title or url)
        return False

    # 3. Classify (always returns a category now, uses 'Genel' as fallback)
    news_type = classify_news(title, content)

    # 4. Extract location (always returns a default Kocaeli location now)
    combined_text = f"{title} {content}"
    location = extract_location(combined_text)
    if not location:
        # Ultimate fallback: center of Kocaeli
        location = {"full_text": "İzmit, Kocaeli", "district": "İzmit", "neighbourhood": None, "street": None}

    # 5. Geocode
    coords = geocode(location["full_text"])
    if not coords:
        logger.warning("[Skip] Geocoding başarısız: %s", location['full_text'])
        return False

    # 6. Embedding-based duplicate check
    embedding = compute_embedding(title, content)
    duplicate = find_duplicate(embedding)

    if duplicate:
        # Merge source into existing news
        db.add_source_to_news(
            duplicate["_id"],
            {"site_name": site_name, "url": url}
        )
        logger.info("[Skip] Benzer haber var (%.0f%%): %s", duplicate['similarity'] * 100, title[:60])
        return False

    # 7. Save new news
    news_doc = {
        "title": title,
        "content": content,
        "news_type": news_type,
        "location_text": location["full_text"],
        "district": location.get("district", ""),
        "neighbourhood": location.get("neighbourhood", ""),
        "street": location.get("street", ""),
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "published_date": article.get("published_date"),
        "sources": [{"site_name": site_name, "url": url}],
        "embedding": embedding,
    }
    db.insert_news(news_doc)
    logger.info("[Saved] %s | %s | %s", title[:60], location.get('district', ''), news_type)
    return True


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Kocaeli Urban News Monitoring System")
    logger.info("Google Maps API Key: %s", 'SET' if GOOGLE_MAPS_API_KEY else 'NOT SET')
    logger.info("=" * 60)
    app.run(debug=True, port=5000, use_reloader=False)

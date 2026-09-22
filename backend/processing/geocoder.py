"""
Geocoding: convert location text → (latitude, longitude).

Uses Google Maps Geocoding API.
Results are cached in MongoDB to prevent redundant API calls.
"""

import time
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import GOOGLE_MAPS_API_KEY, GOOGLE_GEOCODING_API_KEY
from database.mongo_client import db

_LAST_CALL = 0
_geolocator = None

def _get_geolocator():
    global _geolocator
    if _geolocator is None:
        try:
            # Use the dedicated geocoding key if available, otherwise fallback to Maps key
            api_key = GOOGLE_GEOCODING_API_KEY or GOOGLE_MAPS_API_KEY
            
            if not api_key or api_key == "YOUR_GOOGLE_MAP_API_KEY_HERE":
                print("[Geocoder] WARNING: Google Maps API key is missing! Falling back to Nominatim.")
                from geopy.geocoders import Nominatim
                _geolocator = Nominatim(user_agent="KocaeliNewsMonitor/1.0", timeout=10)
                return _geolocator
            
            from geopy.geocoders import GoogleV3
            _geolocator = GoogleV3(api_key=api_key, timeout=10)
        except Exception as e:
            print(f"[Geocoder] Initialization error: {e}")
            from geopy.geocoders import Nominatim
            _geolocator = Nominatim(user_agent="KocaeliNewsMonitor/1.0", timeout=10)
    return _geolocator

def geocode(location_text: str) -> dict | None:
    """
    Convert location text to coordinates.
    Returns {"latitude": float, "longitude": float} or None on failure.
    """
    global _LAST_CALL

    if not location_text:
        return None

    # 1. Aynı konum için gereksiz API çağrısını önle (Cache)
    try:
        cached = db.get_cached_geocode(location_text)
        if cached:
            return {"latitude": cached["latitude"], "longitude": cached["longitude"]}
    except Exception as e:
        print(f"[Geocoder] Cache error: {e}")

    # 2. Rate limit (Google Maps için çok sıkıntı olmasa da fair-use)
    elapsed = time.time() - _LAST_CALL
    if elapsed < 0.2:
        time.sleep(0.2 - elapsed)

    # 3. Google Geocoding API Çağrısı
    geolocator = _get_geolocator()
    if not geolocator:
        return None

    try:
        result = geolocator.geocode(location_text, exactly_one=True)
        _LAST_CALL = time.time()

        if result:
            lat, lon = result.latitude, result.longitude
            try:
                # Başarılı olursa DB'ye kaydet
                db.cache_geocode(location_text, lat, lon)
            except Exception:
                pass
            return {"latitude": lat, "longitude": lon}

        # Daha geniş bağlam için kırp
        parts = [p.strip() for p in location_text.split(",")]
        if len(parts) > 2:
            shorter = ", ".join(parts[1:])
            elapsed = time.time() - _LAST_CALL
            if elapsed < 0.2:
                time.sleep(0.2 - elapsed)
            
            result = geolocator.geocode(shorter, exactly_one=True)
            _LAST_CALL = time.time()
            if result:
                lat, lon = result.latitude, result.longitude
                try:
                    db.cache_geocode(location_text, lat, lon)
                except Exception:
                    pass
                return {"latitude": lat, "longitude": lon}

        return None

    except Exception as e:
        print(f"[Geocoder] Error for '{location_text}': {e}. Attempting Nominatim fallback...")
        try:
            from geopy.geocoders import Nominatim
            fallback = Nominatim(user_agent="KocaeliNewsMonitor/1.0", timeout=10)
            res = fallback.geocode(location_text, exactly_one=True)
            if res:
                lat, lon = res.latitude, res.longitude
                try:
                    db.cache_geocode(location_text, lat, lon)
                except Exception:
                    pass
                return {"latitude": lat, "longitude": lon}
            return None
        except Exception as fallback_e:
            print(f"[Geocoder] Fallback Nominatim also failed: {fallback_e}")
            return None

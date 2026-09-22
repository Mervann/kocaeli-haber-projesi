"""
Location extraction from news text.

Strategy:
  1. Detect Kocaeli district names.
  2. Detect neighbourhood (mahalle) names.
  3. Detect street / boulevard (sokak, cadde, bulvar) names.
  4. Return the most specific location string found.
"""

import re
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import KOCAELI_DISTRICTS

# ── Patterns ──────────────────────────────────────────────────

# Match "XYZ Mahallesi" or "XYZ mahallesi" – captures name
_MAHALLE_RE = re.compile(
    r"([A-ZÇĞİÖŞÜa-zçğıöşü]{2,}(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+)*)\s+[Mm]ahallesi",
    re.UNICODE,
)

# Match "XYZ Sokak/Sokağı/Caddesi/Bulvarı" – captures name
_STREET_RE = re.compile(
    r"([A-ZÇĞİÖŞÜa-zçğıöşü0-9]{2,}(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü0-9]+)*)"
    r"\s+(?:[Ss]oka(?:k|ğı)|[Cc]addesi|[Cc]adde|[Bb]ulvarı|[Bb]ulvar)",
    re.UNICODE,
)

# Match "No: 12" or "No:12" or "No 12" style addresses
_NO_RE = re.compile(r"[Nn]o\s*:?\s*(\d+)", re.UNICODE)


def extract_location(text: str) -> dict | None:
    """
    Extract location from news text.

    Returns dict with keys:
      - district: str | None
      - neighbourhood: str | None
      - street: str | None
      - full_text: str          (combined location string)
    or None if no location found.
    """
    if not text:
        return None

    district = _find_district(text)
    neighbourhood = _find_neighbourhood(text)
    street = _find_street(text)

    # Always default to İzmit if no specific district is found.
    # This ensures ALL Kocaeli news is shown on the map.
    if not district:
        district = "İzmit"

    parts = []
    if street:
        parts.append(street)
    if neighbourhood:
        parts.append(f"{neighbourhood} Mahallesi")
    if district:
        parts.append(district)
    parts.append("Kocaeli")

    return {
        "district": district,
        "neighbourhood": neighbourhood,
        "street": street,
        "full_text": ", ".join(parts),
    }


def _find_district(text: str) -> str | None:
    """Return the first matching Kocaeli district."""
    for d in KOCAELI_DISTRICTS:
        # Case-insensitive search, word boundary
        pattern = re.compile(rf"\b{re.escape(d)}\b", re.IGNORECASE | re.UNICODE)
        if pattern.search(text):
            return d
    # Also handle "ilçe" suffix: "İzmit ilçesi"
    for d in KOCAELI_DISTRICTS:
        pattern = re.compile(
            rf"\b{re.escape(d)}\s+ilçesi\b", re.IGNORECASE | re.UNICODE
        )
        if pattern.search(text):
            return d
    return None


def _find_neighbourhood(text: str) -> str | None:
    """Return the first neighbourhood name found."""
    match = _MAHALLE_RE.search(text)
    return match.group(1).strip() if match else None


def _find_street(text: str) -> str | None:
    """Return the first street/cadde/bulvar name found."""
    match = _STREET_RE.search(text)
    if match:
        street_name = match.group(0).strip()
        # Append number if close by
        remaining = text[match.end():]
        no_match = _NO_RE.match(remaining.lstrip())
        if no_match:
            street_name += f" No:{no_match.group(1)}"
        return street_name
    return None

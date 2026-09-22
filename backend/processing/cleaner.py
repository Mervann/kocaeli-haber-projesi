import re
from bs4 import BeautifulSoup
import unicodedata


def clean_html(raw_html: str) -> str:
    """Remove all HTML tags."""
    soup = BeautifulSoup(raw_html, "lxml")
    # Remove script and style elements
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return text


def remove_extra_whitespace(text: str) -> str:
    """Collapse multiple whitespace into single spaces, strip."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def remove_special_characters(text: str) -> str:
    """Remove unnecessary special characters while keeping Turkish chars."""
    # Keep letters, digits, whitespace, basic punctuation, Turkish specific chars
    text = re.sub(r"[^\w\s.,;:!?''\"()\-–—/&%#@+°₺€$\n]", "", text, flags=re.UNICODE)
    return text


def normalize_text(text: str) -> str:
    """Unicode NFC normalization for consistent Turkish text."""
    return unicodedata.normalize("NFC", text)


def remove_ads_and_noise(text: str) -> str:
    """Remove common ad/noise patterns from Turkish news sites."""
    noise_patterns = [
        r"(?i)reklam\s*alanı",
        r"(?i)sponsorlu\s*içerik",
        r"(?i)devamını\s*oku.*",
        r"(?i)haberin\s*devamı\s*için\s*tıklayınız",
        r"(?i)paylaş\s*:\s*(facebook|twitter|whatsapp|instagram).*",
        r"(?i)(facebook|twitter|instagram|youtube)\s*takip\s*et",
        r"(?i)google\s*haberler",
        r"(?i)bir\s*yorum\s*yaz",
        r"(?i)yorum\s*yap",
        r"(?i)e-?posta\s*adresiniz.*",
        r"(?i)haber\s*kaynağı\s*:",
        r"(?i)abone\s*ol",
        r"(?i)bülten.*kayıt",
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, "", text)
    return text


def clean_text(raw_html: str) -> str:
    """Full cleaning pipeline: HTML → whitespace → special chars → normalize → noise."""
    text = clean_html(raw_html)
    text = remove_ads_and_noise(text)
    text = remove_special_characters(text)
    text = remove_extra_whitespace(text)
    text = normalize_text(text)
    return text

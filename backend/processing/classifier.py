"""Keyword-based news classification.

Priority order (first match wins):
  1. Trafik Kazası
  2. Yangın
  3. Elektrik Kesintisi
  4. Hırsızlık
  5. Kültürel Etkinlikler

DESIGN: Unambiguous standalone words (yangın, hırsızlık, itfaiye) are kept
because they ONLY appear in the context of their category. Ambiguous words
(oyun, gösteri, sergi, etkinlik, sürücü, araç, kaza) are removed because
they appear in unrelated contexts (politics, sports, general news).
"""

# Keywords are stored as lowercase for case-insensitive matching
CATEGORY_KEYWORDS = {
    "Trafik Kazası": [
        # Standalone unambiguous terms
        "trafik kazası", "trafik kazasi", "trafik kazasında",
        "zincirleme kaza", "ölümlü kaza", "yaralanmalı kaza",
        "alkollü sürücü",
        # Compound phrases
        "araç takla", "takla attı",
        "kafa kafaya çarpıştı", "kafa kafaya çarpışma",
        "bariyerlere çarptı", "bariyere çarptı",
        "direğe çarptı", "duvara çarptı", "ağaca çarptı",
        "yayaya çarptı", "yayaya çarpan",
        "yaya geçidinde", "yayaya çarparak",
        "araçla çarpıştı", "otomobille çarpıştı",
        "otobüs kazası", "motosiklet kazası", "minibüs kazası",
        "tır kazası", "araç kazası", "otomobil kazası",
        "kırmızı ışıkta geçti", "kırmızı ışık ihlali",
        "trafik denetimi", "yoldan çıktı", "yoldan çıkan",
        "otoyolda kaza", "makas atan", "makas atarak",
        "kaza anı", "kaza sonucu",
        "çarpışma sonucu", "çarpışarak",
        "hız ihlali", "hız yapan",
        "kazada yaralandı", "kazada hayatını kaybetti",
        "kazada öldü", "kaza meydana geldi",
        "araçlara çarptı", "araca çarptı",
        "park halindeki araca", "park halindeki araçlara",
        "çarpıştı",  # catches "tramvayla çarpıştı", "araba çarpıştı" etc.
        "kaldırıma çıktı", "kaldırıma çıkan",
        "kaza yaptı", "kaza yapan",
        "servisi kaza", "servis aracı kaza",
        "otomobil kaldırıma",
        "motosiklet beton", "motosiklet bariyere",
    ],
    "Yangın": [
        # Standalone unambiguous terms — "yangın" is very specific
        "yangın", "yangin", "yangında", "yangını", "yangınına",
        "yangınlar", "yangınları",
        "itfaiye", "kundaklama", "kundaklandı", "kundaklanan",
        "alevlere teslim", "alevler sardı", "alevler yükseldi",
        # Compound phrases
        "söndürme çalışması", "söndürme çalışmaları",
        "dumandan etkilendi", "dumandan zehirlendi",
        "alev alev yandı", "alev alev yaktı",
        "alev aldı", "tutuştu",
    ],
    "Elektrik Kesintisi": [
        "elektrik kesintisi", "elektrik kesintileri",
        "enerji kesintisi", "enerji kesintileri",
        "elektrikler kesildi", "elektrikler kesilecek",
        "elektrik gidecek", "elektrikler gitti",
        "elektrik verilmeyecek", "elektrik verilemeyecek",
        "trafo patladı", "trafo arızası",
        "şebeke arızası", "şebeke kesintisi",
        "planlı kesinti", "programlı kesinti",
        "sedaş kesinti", "sedaş duyuru", "sedaş",
    ],
    "Hırsızlık": [
        # Standalone unambiguous terms
        "hırsızlık", "hirsizlik", "hırsızlar", "hırsız",
        "gasp", "gaspçı", "kapkaç", "kapkaççı", "yankesici",
        "soygun", "soygunu",
        # Compound phrases
        "çaldığı iddia", "çalınan eşya",
        "çaldı yakalandı", "çalan şüpheli",
    ],
    "Kültürel Etkinlikler": [
        # Standalone unambiguous terms — these ONLY appear in cultural contexts
        "konser", "festival", "festivali",
        "tiyatro", "orkestra",
        "fuar", "fuarı",
        "sempozyum", "resital",
        "maraton",
        # Compound phrases — avoids false positives from ambiguous words
        "sergi açıldı", "sergisi açıldı", "sergi düzenlendi",
        "resim sergisi", "fotoğraf sergisi", "sanat sergisi",
        "kültürel etkinlik", "kültür etkinliği",
        "şenlik düzenlendi", "şenliğe katıldı",
        "panel düzenlendi", "seminer düzenlendi",
        "konferans düzenlendi",
        "söyleşi düzenlendi", "söyleşi etkinliği",
        "atölye çalışması", "workshop",
        "müzik dinletisi", "müzik gecesi",
        "film gösterimi", "belgesel gösterimi",
        "kermes düzenlendi", "kermes etkinliği",
        "ödül töreni", "açılış töreni",
        "turnuva düzenlendi", "spor müsabakası",
        "sahne aldı", "sahneye çıktı",
        "dans gösterisi",
    ],
}

# Priority order: first match wins
PRIORITY_ORDER = [
    "Trafik Kazası",
    "Yangın",
    "Elektrik Kesintisi",
    "Hırsızlık",
    "Kültürel Etkinlikler",
]


def classify_news(title: str, content: str) -> str:
    """
    Classify news based on keyword matching with priority.

    Returns the news type string. Falls back to 'Genel' if no specific
    category matches, so all news is kept on the map.
    """
    combined = f"{title} {content}".lower()

    for category in PRIORITY_ORDER:
        keywords = CATEGORY_KEYWORDS[category]
        for kw in keywords:
            if kw in combined:
                return category

    return "Genel"  # Fallback: show all news on the map

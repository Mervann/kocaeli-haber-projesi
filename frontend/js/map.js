/**
 * map.js – Google Maps Map initialization and marker management
 */

// ── Map Configuration ─────────────────────────────────────
const KOCAELI_CENTER = { lat: 40.7654, lng: 29.9408 };
const DEFAULT_ZOOM = 11;

// Category → Google Marker Colors
const MARKER_COLORS = {
    "Trafik Kazası":      "http://maps.google.com/mapfiles/ms/icons/red-dot.png",
    "Yangın":             "http://maps.google.com/mapfiles/ms/icons/orange-dot.png",
    "Elektrik Kesintisi": "http://maps.google.com/mapfiles/ms/icons/yellow-dot.png",
    "Hırsızlık":          "http://maps.google.com/mapfiles/ms/icons/purple-dot.png",
    "Kültürel Etkinlikler": "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
};

const TYPE_CLASS_MAP = {
    "Trafik Kazası":      "type-trafik",
    "Yangın":             "type-yangin",
    "Elektrik Kesintisi": "type-elektrik",
    "Hırsızlık":         "type-hirsizlik",
    "Kültürel Etkinlikler": "type-kultur",
};

// ── State ─────────────────────────────────────────────────
let map = null;
let markers = [];
let infoWindow = null;

// ── Init ──────────────────────────────────────────────────
window.initMap = function() {
    map = new google.maps.Map(document.getElementById("map"), {
        center: KOCAELI_CENTER,
        zoom: DEFAULT_ZOOM,
        mapTypeId: "roadmap",
        // Standart Google Maps teması kullanılması istendiği için styles kaldırıldı
    });

    infoWindow = new google.maps.InfoWindow();

    // Trigger loading data after map is fully initialized
    setupFilterListeners();
    loadNews();
    loadDistricts();
};

// ── Marker Management ─────────────────────────────────────

function clearMarkers() {
    markers.forEach(m => m.setMap(null));
    markers = [];
}

function addNewsMarkers(newsItems) {
    clearMarkers();
    const seenLocs = {};

    newsItems.forEach((news) => {
        if (!news.latitude || !news.longitude) return;

        let lat = parseFloat(news.latitude);
        let lng = parseFloat(news.longitude);

        // Prevent marker stacking (Jitter)
        const locKey = `${lat.toFixed(4)},${lng.toFixed(4)}`;
        if (seenLocs[locKey]) {
            seenLocs[locKey]++;
            const offset = seenLocs[locKey] * 0.0003; 
            const angle = seenLocs[locKey] * Math.PI * 0.618;
            lat += Math.cos(angle) * offset;
            lng += Math.sin(angle) * offset;
        } else {
            seenLocs[locKey] = 1;
        }

        const iconUrl = MARKER_COLORS[news.news_type] || MARKER_COLORS["Trafik Kazası"];

        const marker = new google.maps.Marker({
            position: { lat: lat, lng: lng },
            map: map,
            icon: iconUrl,
            title: news.title
        });

        marker.originalLat = news.latitude;
        marker.originalLng = news.longitude;
        marker.newsData = news;

        // Add Click Listener
        marker.addListener("click", () => {
            infoWindow.setContent(createPopupContent(news));
            infoWindow.open(map, marker);
        });

        markers.push(marker);
    });
}

function createPopupContent(news) {
    const typeClass = TYPE_CLASS_MAP[news.news_type] || "type-genel";

    // Format date
    let dateStr = "—";
    if (news.published_date) {
        try {
            const d = new Date(news.published_date);
            dateStr = d.toLocaleDateString("tr-TR", {
                year: "numeric", month: "long", day: "numeric",
                hour: "2-digit", minute: "2-digit"
            });
        } catch {
            dateStr = news.published_date;
        }
    }

    // Sources list
    const sources = (news.sources || []).map((s) =>
        `<a href="${s.url}" target="_blank" rel="noopener" class="popup-source-link" style="color:#007bff; text-decoration:none;">
            ${s.site_name}
        </a>`
    ).join("&nbsp;|&nbsp;");

    const firstUrl = news.sources && news.sources.length > 0 ? news.sources[0].url : "#";

    return `
        <div style="max-width:300px; font-family:'Inter',sans-serif; color:#333;">
            <div style="font-size:12px; font-weight:bold; color:#777; margin-bottom:5px;">${news.news_type}</div>
            <div style="font-size:16px; font-weight:bold; margin-bottom:8px; line-height:1.2;">${news.title}</div>
            <div style="font-size:13px; margin-bottom:4px;">
                <strong>Tarih:</strong> ${dateStr}
            </div>
            <div style="font-size:13px; margin-bottom:10px;">
                <strong>Konum:</strong> ${news.location_text || news.district || "—"}
            </div>
            <div style="font-size:13px; margin-bottom:10px;">
                <strong>Kaynaklar:</strong> ${sources}
            </div>
            <a href="${firstUrl}" target="_blank" rel="noopener" style="display:inline-block; padding:6px 12px; background:#007bff; color:#fff; border-radius:4px; text-decoration:none; font-size:13px;">
                Habere Git
            </a>
        </div>
    `;
}

function focusMarker(lat, lng) {
    if (map) {
        map.panTo({ lat, lng });
        map.setZoom(15);
        
        // Find and open popup
        markers.forEach((m) => {
            const pos = m.getPosition();
            // Google Maps uses .lat() and .lng() methods
            if (Math.abs(pos.lat() - parseFloat(lat)) < 0.0001 && Math.abs(pos.lng() - parseFloat(lng)) < 0.0001) {
                new google.maps.event.trigger(m, 'click');
            }
        });
    }
}

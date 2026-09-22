/**
 * app.js – Main application logic
 * Coordinates data fetching, filtering, and UI updates.
 */

const API_BASE = ""; // Same origin (served by Flask)

let allNews = []; // All news from server

// ── Init ──────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    loadGoogleMaps();
});

async function loadGoogleMaps() {
    try {
        // Force the browser to bypass cache by adding a timestamp query string
        const resp = await fetch(`${API_BASE}/api/config?t=${new Date().getTime()}`, {
            cache: 'no-store'
        });
        const data = await resp.json();
        const apiKey = data.google_maps_api_key;
        
        if (!apiKey || apiKey === "YOUR_GOOGLE_MAPS_API_KEY_HERE") {
            console.error("Missing Google Maps API Key.");
            const overlay = document.getElementById("loading-overlay");
            if (overlay) {
                overlay.style.display = "flex";
                overlay.innerHTML = `<div class="loading-content"><p style="color:red; font-weight:bold;">HATA: Google Maps API Anahtarı eksik! (.env dosyasını kontrol edin)</p></div>`;
            }
            return;
        }

        // Dynamically load Google Maps script
        const script = document.createElement("script");
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initMap`;
        script.async = true;
        // Don't use defer alongside async to ensure rapid load before dom manipulations
        document.head.appendChild(script);

    } catch (err) {
        console.error("Failed to load map config:", err);
    }
}

// ── Data Loading ──────────────────────────────────────────

async function loadNews() {
    showLoading(true);
    try {
        const resp = await fetch(`${API_BASE}/api/news`);
        const data = await resp.json();
        allNews = data.news || [];
        applyFilters();
        document.getElementById("news-count").textContent = allNews.length;
    } catch (err) {
        console.error("Failed to load news:", err);
        allNews = [];
    }
    showLoading(false);
}

async function loadDistricts() {
    try {
        const resp = await fetch(`${API_BASE}/api/news/districts`);
        const data = await resp.json();
        populateDistrictFilter(data.districts || []);
    } catch (err) {
        console.error("Failed to load districts:", err);
    }
}

// ── Filtering ─────────────────────────────────────────────

function filterAndDisplayNews(filters) {
    let filtered = allNews;

    // Filter by types
    if (filters.types && filters.types.length > 0) {
        filtered = filtered.filter((n) => filters.types.includes(n.news_type));
    }

    // Filter by district
    if (filters.district) {
        filtered = filtered.filter((n) => n.district === filters.district);
    }

    // Filter by date range
    if (filters.dateFrom) {
        const from = new Date(filters.dateFrom);
        filtered = filtered.filter((n) => {
            if (!n.published_date) return false;
            return new Date(n.published_date) >= from;
        });
    }
    if (filters.dateTo) {
        const to = new Date(filters.dateTo);
        to.setHours(23, 59, 59);
        filtered = filtered.filter((n) => {
            if (!n.published_date) return false;
            return new Date(n.published_date) <= to;
        });
    }

    // Update UI
    addNewsMarkers(filtered);
    updateNewsList(filtered);
    updateTypeCounts(filtered);
    document.getElementById("news-count").textContent = filtered.length;
}

// ── News List ─────────────────────────────────────────────

function updateNewsList(newsItems) {
    const container = document.getElementById("news-list");

    if (newsItems.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M16 16s-1.5-2-4-2-4 2-4 2"/>
                    <line x1="9" y1="9" x2="9.01" y2="9"/>
                    <line x1="15" y1="9" x2="15.01" y2="9"/>
                </svg>
                <p>Henüz haber bulunamadı.</p>
                <p>Haberleri çekmek için "Haberleri Çek" butonuna tıklayın.</p>
            </div>`;
        return;
    }

    container.innerHTML = newsItems
        .slice(0, 50) // Show max 50 in sidebar
        .map((n) => {
            let dateStr = "";
            if (n.published_date) {
                try {
                    const d = new Date(n.published_date);
                    dateStr = d.toLocaleDateString("tr-TR", { day: "numeric", month: "short" });
                } catch {
                    dateStr = "";
                }
            }
            const sourceName = n.sources && n.sources.length > 0 ? n.sources[0].site_name : "";

            return `
                <div class="news-item" data-type="${n.news_type}"
                     onclick="focusMarker(${n.latitude}, ${n.longitude})">
                    <div class="news-item-title">${n.title}</div>
                    <div class="news-item-meta">
                        <span>${n.news_type}</span>
                        <span>·</span>
                        <span>${n.district || ""}</span>
                        <span>·</span>
                        <span>${dateStr}</span>
                    </div>
                </div>`;
        })
        .join("");
}

// ── Scraping ──────────────────────────────────────────────

async function triggerScrape() {
    const btn = document.getElementById("btn-scrape");
    btn.disabled = true;

    const statusSection = document.getElementById("scrape-status-section");
    const statusMsg = document.getElementById("scrape-message");
    statusSection.style.display = "block";
    statusMsg.textContent = "Başlatılıyor...";

    try {
        const resp = await fetch(`${API_BASE}/api/scrape`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ days: 3 }),
        });

        if (resp.status === 409) {
            statusMsg.textContent = "Scraping zaten çalışıyor...";
            return;
        }

        // Poll status
        pollScrapeStatus();
    } catch (err) {
        console.error("Scrape trigger failed:", err);
        statusMsg.textContent = "Hata: " + err.message;
        btn.disabled = false;
    }
}

async function pollScrapeStatus() {
    const statusMsg = document.getElementById("scrape-message");
    const statusSection = document.getElementById("scrape-status-section");
    const btn = document.getElementById("btn-scrape");

    const poll = async () => {
        try {
            const resp = await fetch(`${API_BASE}/api/scrape/status`);
            const data = await resp.json();
            statusMsg.textContent = data.message || "Çalışıyor...";

            if (data.running) {
                setTimeout(poll, 2000);
            } else {
                btn.disabled = false;
                // Reload news after scrape completes
                setTimeout(() => {
                    statusSection.style.display = "none";
                    loadNews();
                    loadDistricts();
                }, 1500);
            }
        } catch (err) {
            statusMsg.textContent = "Durum sorgusu başarısız.";
            btn.disabled = false;
        }
    };

    setTimeout(poll, 2000);
}

// ── Helpers ───────────────────────────────────────────────

function showLoading(show) {
    document.getElementById("loading-overlay").style.display = show ? "flex" : "none";
}

// ── Stats Modal ──────────────────────────────────────────────

function openStatsModal() {
    const overlay = document.getElementById("stats-modal-overlay");
    if (!overlay) return;
    
    populateStatsModal();
    overlay.style.display = "flex";
}

function closeStatsModal(event) {
    // If event is provided, only close if clicking the overlay itself
    if (event && event.target && event.target.id !== "stats-modal-overlay") return;
    
    const overlay = document.getElementById("stats-modal-overlay");
    if (overlay) overlay.style.display = "none";
}

function populateStatsModal() {
    const body = document.getElementById("stats-modal-body");
    if (!body) return;
    
    // Group news by source
    const stats = {};
    let totalCount = 0;
    
    allNews.forEach(news => {
        let sourceName = "Bilinmiyor";
        let url = "#";
        if (news.sources && news.sources.length > 0) {
            sourceName = news.sources[0].site_name || "Bilinmiyor";
            url = news.sources[0].url || "#";
        }
        
        if (!stats[sourceName]) {
            stats[sourceName] = { count: 0, items: [] };
        }
        stats[sourceName].count++;
        stats[sourceName].items.push({
            title: news.title,
            type: news.news_type,
            url: url
        });
        totalCount++;
    });
    
    if (totalCount === 0) {
        body.innerHTML = `
            <div class="empty-state">
                <p>Henüz kayıtlı haber yok.</p>
            </div>
        `;
        return;
    }
    
    // Convert to array and sort by count descending
    const sortedStats = Object.entries(stats).sort((a, b) => b[1].count - a[1].count);
    
    let html = "";
    sortedStats.forEach(([source, data]) => {
        const itemsHtml = data.items.map(item => `
            <div class="stats-news-item">
                <a href="${item.url}" target="_blank" title="${item.title}">${item.title}</a>
                <span class="stats-news-type">${item.type}</span>
            </div>
        `).join("");
        
        html += `
            <div class="stats-source-group">
                <div class="stats-source-header">
                    <span>${source}</span>
                    <span class="stats-source-count">${data.count} Haber</span>
                </div>
                <div class="stats-news-list">
                    ${itemsHtml}
                </div>
            </div>
        `;
    });
    
    body.innerHTML = html;
}

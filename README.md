# 📰 Kocaeli News Aggregator & Web Scraper

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Scraper-Cloudscraper_%2B_curl__cffi-FF6C37?style=for-the-badge&logo=postman&logoColor=white" alt="Web Scraper" />
  <img src="https://img.shields.io/badge/Frontend-Modern_Web_UI-38BDF8?style=for-the-badge&logo=html5&logoColor=white" alt="Web UI" />
  <img src="https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge" alt="License" />
</div>

<br/>

> **Kocaeli News Aggregator** is an automated web scraping, data pipeline, and news publishing platform built using Python and modern web frontend components. The system features advanced anti-bot bypass strategies (`cloudscraper` and `curl_cffi`), automatic pagination handling, title & date verification, and a dynamic web interface for news consumption.

---

## 📐 Data Pipeline Architecture Flowchart

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AUTOMATED PYTHON SCRAPER                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Anti-Bot Bypass Layer (cloudscraper / curl_cffi / Headers)     │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ HTTP Request Engine                │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ BeautifulSoup4 Parsing Engine & Pagination Harvester           │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │ Extracted Articles
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA CLEANING & STORAGE                         │
│  - Date Verification (`verify_dates.py`)                               │
│  - Deduplication & Pagination Parsing (`test_pagination.py`)            │
│  - JSON / Database Export                                              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Structured News Data
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       DYNAMIC FRONTEND DASHBOARD                       │
│  [ Category Filters + Pagination Control + Visual Alert Banners ]     │
└───────────────────────────────────┴────────────────────────────────────┘
```

---

## 🛠️ Key Modules & Feature Breakdown

| Module | Purpose | Implementation Detail |
| :--- | :--- | :--- |
| **Scraper Engine** | Anti-Bot Scraping | Built with `cloudscraper` & `curl_cffi` to bypass Cloudflare protection |
| **Pagination Handler** | Multi-Page Harvesting | Traverses paginated news listings seamlessly |
| **Date Verifier** | Data Sanitization | Validates publication dates and filters outdated entries (`verify_dates.py`) |
| **Frontend UI** | Category Feeds | Displays news with responsive image grids and status badges |
| **Trigger System** | Automated Scheduling | `trigger_scrape.py` script for periodic background execution |

---

## 📖 Complete User & Developer Guide

### 🛠️ Prerequisites & Installation

1. **Clone Repository:**
   ```bash
   git clone https://github.com/Mervann/kocaeli-haber-projesi.git
   cd kocaeli-haber-projesi
   ```

2. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Scraper Pipeline:**
   ```bash
   python trigger_scrape.py
   ```

4. **Verify Extracted Dates & Articles:**
   ```bash
   python verify_dates.py
   ```

5. **Open Frontend Web Portal:**
   Navigate to the `frontend/` directory and open `index.html` in your web browser.

---

## 👨‍💻 Author Information

Developed by **Mervan Elbahadır**  
🎓 *Computer Engineering Student @ Kocaeli University*  
📫 Contact: `mervanelbahadir587@gmail.com`  
🌐 Profile: [github.com/Mervann](https://github.com/Mervann)

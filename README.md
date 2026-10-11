# 🚀 AI Career Copilot — Otonom İş Arama & Kariyer Asistanı

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-3.8%20Flash-8E75B2.svg?logo=google-gemini&logoColor=white)](https://aistudio.google.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-2CA5E0.svg?logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![cron-job.org](https://img.shields.io/badge/Scheduler-cron--job.org-green.svg)](https://cron-job.org)
[![Platforms](https://img.shields.io/badge/Platforms-LinkedIn%20%7C%20Kariyer.net-orange.svg)](#)
[![Location](https://img.shields.io/badge/Location-Sadece%20İstanbul-success.svg)](#)

> **AI Career Copilot**, iş arama ve eleme sürecini uçtan uca otomatikleştiren, **Google Gemini** bilişsel motoruyla semantik eşleşme yapan ve Telegram üzerinden anlık başvuru paketleri sunan hafif, kararlı ve sıfır-hata odaklı bir kariyer asistanıdır.

---

## 🌟 Öne Çıkan Özellikler

* **🇹🇷 İki Büyük Platform (LinkedIn + Kariyer.net):**
  * LinkedIn Guest API ve Kariyer.net üzerinden güncel (son 24 saat) ilanları üyelik gerektirmeden kararlı şekilde çeker.
* **📍 %100 Kesin İstanbul Lokasyon Doğrulaması:**
  * Denizli, Tekirdağ, Ankara, İzmir gibi şehir dışı ilanlar ve belirsiz genel konumlar baştan elenir. Sadece İstanbul yerelindeki fırsatlar incelenir.
* **🎯 Pozitif Alan Filtresi & Temiz Teknoloji Odaklanması:**
  * Alakasız unvanlar (satış, çağrı merkezi, cerrahi robot, fiyatlandırma vb.) ve adayın uzmanlığı dışındaki teknolojiler (.NET, C#, Flutter, iOS Swift, Unity) doğrudan filtrelenir.
  * Adayın gerçek gücüne (C/C++ Sistem, Node.js/NestJS Backend, React Native Mobil, Astro Frontend, AI & IT Stajı) tam uyumlu roller hedeflenir.
* **🧠 Google Gemini Semantik Değerlendirmesi:**
  * `gemini-flash-latest` ve `gemini-3.8-flash` modelleriyle ilanın görev tanımını derinlemesine analiz eder; mülakatta arkasında durulabilecek %100 dürüst eşleşme puanı üretir.
* **💬 0–400 Karakterlik LinkedIn Kolay Başvuru Notu:**
  * LinkedIn mobil uygulamasındaki *"Başvurunuzla birlikte bir mesaj ekleyin (0/400)"* alanına özel, Python seviyesinde **$\le$ 400 karakter** garantili, teknik ve samimi başvuru mesajı üretir.
* **📱 Zengin Telegram Bildirim Kartları & Tek Dokunuş Başvuru:**
  * Uyum puanına göre doğru rozetler:
    * 🎯 **GÜÇLÜ EŞLEŞME** ($\ge$ %65)
    * 💡 **DENENEBİLİR İLAN** (%50 – %64)
    * Asla düşük puanlı ilanlara yanıltıcı başlık basılmaz.
  * Dokun-kopyala kod bloğu ve doğrudan başvuru butonu (`[ 🚀 Kolay Başvur ]` / `[ 🌐 İlana Git ]`).
* **💾 SQLite ile Mükerrer Önleme (Deduplication):**
  * Taranan tüm ilanlar `applications.db` içinde saklanır; aynı ilan asla ikinci kez incelenmez veya bildirilmez.
* **⚡ Ultra Hafif & Hızlı CI/CD (GitHub Actions + cron-job.org):**
  * Ağır ve kırılgan tarayıcı otomasyonları (Playwright) kaldırılmıştır. Sistem bulut ortamında 1-2 dakika içinde hafifçe çalışır ve tamamlanır.

---

## 🏗️ Sistem Mimarisi

```mermaid
flowchart TD
    Trigger["cron-job.org (Vardiya Tetiklemesi)"] --> GH["GitHub Actions Runner / Yerel CLI"]
    GH --> Scraper["JobScraperManager (LinkedIn + Kariyer.net)"]
    
    Scraper --> Deduplicate{"Daha Önce Taranmış mı?<br>(applications.db)"}
    Deduplicate -->|Evet| SkipSeen["Atla (Mükerrer Önleme)"]
    Deduplicate -->|Hayır| LocFilter{"Lokasyon Filtresi<br>(Sadece İstanbul mu?)"}
    
    LocFilter -->|Hayır| SkipLoc["Atla & DB Kaydet (SKIPPED)"]
    LocFilter -->|Evet| DomainFilter{"Alan Doğrulama<br>(Yazılım/Bilişim & Hedef Rol mü?)"}
    
    DomainFilter -->|Hayır| SkipDomain["Atla & DB Kaydet (SKIPPED)"]
    DomainFilter -->|Evet| Details["İlan Detayı Çekimi"]
    
    Details --> Gemini["Google Gemini API (Semantik Analiz)"]
    Gemini --> Decision{"Uyum Skoru & Karar"}
    
    Decision -->|< %50 / Reddedildi| SkipAI["Atla & DB Kaydet (SKIPPED)"]
    Decision -->|>= %50 (Uygun)| Telegram["📱 Telegram Zengin Bildirim Kartı<br>• Uyum Skoru & Rozet<br>• Dokun-Kopyala 400 Karakter Not<br>• Doğrudan Başvuru Butonu"]
    
    Telegram --> SaveDB["Veritabanına Kaydet (NOTIFIED)"]
    SaveDB --> Report["Günlük Markdown Raporu & Git Auto-Commit"]
```

---

## 📂 Dizin Yapısı

```text
├── .github/workflows/
│   └── daily_pipeline.yml       # Hafif ve hızlı GitHub Actions iş akışı
├── config/
│   ├── candidate_profile.yaml   # Adayın doğrulanmış tek gerçeklik kaynağı
│   └── search_config.yaml       # Taranan sorgular, İstanbul konumu ve eşik değerleri
├── core/
│   ├── models.py                # JobPosting ve ReviewResult veri modelleri
│   ├── location_filter.py       # Kesin ve sıkı İstanbul doğrulama motoru
│   ├── domain_filter.py         # Pozitif alan ve alan dışı teknoloji filtresi
│   ├── database.py              # SQLite bağlantı ve çift kayıt önleyici motor
│   ├── ai_reviewer.py           # Gemini semantik analizi ve 400 karakter not üretimi
│   ├── notifier.py              # Zengin Telegram HTML kartları ve istatistik bildirimi
│   ├── orchestrator.py          # Tüm bileşenleri koordine eden ana orkestratör
│   └── scrapers/
│       ├── base.py              # Temel scraper soyut sınıfı
│       ├── linkedin_scraper.py  # LinkedIn Guest API scraper
│       ├── kariyernet_scraper.py# Kariyer.net scraper
│       └── manager.py           # Birleşik scraper yöneticisi
├── source_resume/
│   ├── Omer_Faruk_Gokdas_CV_Master_ATS.pdf     # 92 puanlık doğrulanmış tek sayfa ATS CV
│   └── Omer_Faruk_Gokdas_CV_Master_ATS_TR.pdf  # Türkçe ATS CV
├── tests/
│   ├── test_location_filter.py  # Lokasyon filtresi birim testleri
│   ├── test_domain_filter.py    # Alan filtresi birim testleri
│   ├── test_database.py         # DB ve tekilleştirme testleri
│   ├── test_ai_reviewer.py      # AI inceleme ve 400 karakter not testleri
│   ├── test_notifier.py         # Telegram kart formatı testleri
│   ├── test_scrapers.py         # Scraper parse testleri
│   └── test_e2e_orchestrator.py # Uçtan uca entegrasyon testi
├── applications.db              # SQLite takip veritabanı
├── run_automation.py            # Ana çalıştırma CLI aracı
├── requirements.txt             # Minimal Python bağımlılıkları (requests, pyyaml, python-dotenv)
└── README.md                    # Proje dokümantasyonu
```

---

## ⚡ Hızlı Başlangıç & Yerel Çalıştırma

### 1. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Ortam Değişkenlerini Tanımlayın (`.env`)
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-flash-latest

TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TELEGRAM_ENABLED=true
```

### 3. Çalıştırma
```bash
# Tam tarama yap
python run_automation.py

# Belirli vardiya ile çalıştır (1: Sabah, 2: Öğle)
python run_automation.py --shift 1

# Test amaçlı sorgu başına maksimum 2 ilanla sınırla
python run_automation.py --limit 2
```

### 4. Tüm Testleri Çalıştırın
```bash
python -m unittest discover tests
```

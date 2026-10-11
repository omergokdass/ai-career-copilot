# AI Career Copilot — Sistem Durumu & Doğrulanmış Mimari

Bu belge, projenin sıfırdan yeniden inşa edilen teknik durumunu, doğrulanmış mimari kararlarını ve kalite güvence standartlarını özetler.

---

### 1. Aday Profili (Tek Gerçeklik Kaynağı - %100 Doğrulanmış)
- **Aday:** Ömer Faruk Gökdaş (İstanbul)
- **Eğitim:**
  - Nişantaşı Üniversitesi - Yazılım Mühendisliği Lisans (**Eylül 2021 - Temmuz 2026**)
  - 42 İstanbul (Ecole 42) - Sistem Programlama ve Yazılım Mühendisliği (**Ocak 2025 - Devam Ediyor**)
- **İhbar Süresi:** 0 Gün (Hemen Başlayabilir / Askerlik Tecilli)
- **Doğrulanmış Projeler:**
  - `CoupleOS`: React Native (Expo), TypeScript, NestJS, Prisma ORM, Socket.IO, Supabase PostgreSQL, Zustand, Multi-LLM (Gemini & OpenAI).
  - `branda.ist`: 80+ sayfalık canlı ticari web platformu (Astro, TypeScript, SSG, Sharp, PurgeCSS, Programatik SEO).
  - `Minishell & Philosophers` (42 Istanbul): POSIX Unix shell, process control, pipes, Valgrind sızıntısız bellek yönetimi, multithreading & mutex.
  - `NishChat` (Bitirme Projesi): Node.js, Express, Socket.IO, PostgreSQL gerçek zamanlı mesajlaşma platformu.
  - `Beşiktaş Belediyesi Stajı`: Active Directory, TCP/IP, kurumsal IT desteği, Bash otomasyonu.
- **Kesin Kural:** Adayın bilmediği / uzmanlığı dışındaki teknolojiler (.NET, C#, Java Spring, Swift/iOS Native, Flutter, SAP, Kubernetes, AWS vb.) asla uydurulmaz veya eşleşme sebebi sayılamaz.

---

### 2. Yeniden İnşa Edilen Temiz Mimari Kararları
- **Lokasyon Doğrulaması:**
  - Kesin kural: SADECE İstanbul.
  - Denizli, Tekirdağ, Ankara, Bursa, İzmir veya belirsiz Türkiye/Remote ilanları baştan elenir (`core/location_filter.py`).
- **Pozitif Alan Doğrulaması:**
  - Yazılım, sistem, backend, frontend, mobil, AI veya IT staj rolleri onaylanır; satış, pazarlama, çağrı merkezi, tıp, cerrahi robot, konveyör gibi alakasız meslekler baştan elenir (`core/domain_filter.py`).
- **Google Gemini Entegrasyonu:**
  - Desteklenen modeller: `gemini-flash-latest` ve `gemini-3.8-flash`.
  - JSON formatında kesin semantik analiz.
  - Kesin **$\le$ 400 Karakter** LinkedIn Easy Apply not garantisi.
  - Ağ kesintisi veya kota aşımı durumunda çalışan deterministik yerel kural motoru.
- **Telegram Notifier:**
  - Uyum skoruna göre kesin rozet:
    - $\ge$ %65: 🎯 GÜÇLÜ EŞLEŞME
    - %50 - %64: 💡 DENENEBİLİR İLAN (SINIRDA)
    - Asla düşük puanlı ilana "Güçlü Eşleşme" denmez.
  - Dokun-kopyala kod bloğu ve doğrudan başvuru butonu.
- **Veritabanı & Mükerrer Önleme:**
  - `applications.db` SQLite veritabanı. İlan URL'si tekil anahtardır; aynı ilan asla ikinci kez taranmaz.
- **CI/CD & Dağıtım:**
  - Playwright kaldırıldı; hafif `requests` + `pyyaml` tabanlı hızlı ve stabil mimariye geçildi.
  - GitHub Actions üzerinde 1-2 dakikada hatasız tamamlanır.

---

### 3. Kalite Güvence ve Testler
- 17 birim ve entegrasyon testinin tamamı (%100) başarıyla geçmektedir:
  - Lokasyon filtreleme testleri (İstanbul ilçeleri kabul, Denizli/Tekirdağ/Ankara ret)
  - Alan filtreleme testleri (Yazılım rolleri kabul, alakasız meslekler ve C#/.NET ret)
  - SQLite veritabanı ve tekilleştirme testleri
  - AI Reviewer 400 karakter not sınırı ve puanlama testleri
  - Telegram Notifier kart ve rozet testleri
  - Scraper parsing testleri
  - Uçtan uca (E2E) orchestrator pipeline testi

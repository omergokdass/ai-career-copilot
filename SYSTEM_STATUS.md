# LinkedIn & Kariyer.net Job Agent — Sistem Durumu

Bu dosya, projenin mevcut teknik durumunu, doğrulanmış mimari kararları ve çalışma standartlarını özetler.

---

### 1. Aday Profili (Tek Gerçeklik Kaynağı - %100 Doğrulanmış)
- **Aday:** Ömer Faruk Gökdaş (İstanbul)
- **Eğitim:**
  - Nişantaşı Üniversitesi - Yazılım Mühendisliği Lisans Mezuniyeti (**Eylül 2021 - Temmuz 2026**)
  - 42 İstanbul (Ecole 42) - Sistem Programlama ve Yazılım Mühendisliği (**Ocak 2025 - Devam Ediyor**)
- **İhbar Süresi:** 0 Gün (Hemen Başlayabilir)
- **Doğrulanmış Projeler:**
  - `CoupleOS`: React Native (Expo), TypeScript, NestJS, Prisma ORM, Socket.IO, Supabase PostgreSQL, Zustand, Gemini & OpenAI Multi-LLM entegrasyonu.
  - `branda.ist`: 80+ sayfalık canlı ticari web platformu (Astro, TypeScript, SSG, Sharp, PurgeCSS, Programatik SEO).
  - `Minishell & Philosophers` (42 Istanbul): POSIX Unix shell, process control, pipes, Valgrind sızıntısız bellek yönetimi, multithreading & mutex.
  - `NishChat` (Bitirme Projesi): Node.js, Express, Socket.IO, PostgreSQL gerçek zamanlı mesajlaşma platformu.
  - `Beşiktaş Belediyesi Stajı`: Active Directory, TCP/IP, kurumsal IT desteği, Bash otomasyonu.
- **Kesin Kural:** Adayın yapmadığı hiçbir sahte teknoloji (Spring Boot 3, Redis, AWS, Kubernetes, Flutter, Swift vb.) uydurulamaz.

---

### 2. Başvuru ve Dil Kuralları
- **CV Dosyası (Sabit Kural):** İlan Türkçe de olsa İngilizce de olsa **HER ZAMAN 92 puanlık İngilizce Master ATS CV** kullanılır:
  `source_resume/Omer_Faruk_Gokdas_CV_Master_ATS.pdf`
- **Ön Yazı (Cover Letter) Dili:**
  - İlan Türkçe ise: Kurumsal ve akıcı **Türkçe Ön Yazı**.
  - İlan İngilizce ise: Şirket odaklı profesyonel **İngilizce Cover Letter**.
- **İki Kademeli Triage:**
  - `%70+`: Güçlü Eşleşme (`STRONG` / `RECOMMENDED`)
  - `%50 - %69`: Sınırda / Denenebilir İlan (`BORDERLINE` - "Düşük İhtimal / Denenebilir")
  - `<%50`: Elendi (`SKIP`)

---

### 3. Aktif Entegrasyonlar ve Tamamlanan Düzeltmeler
- **Çoklu Platform:** LinkedIn Guest API + Kariyer.net birleşik arama motoru (`MultiPlatformScraper`).
- **Google Gemini 2.5 Flash:** REST API üzerinden çalışan semantik analiz ve çoklu fallback zinciri (`gemini-2.5-flash` -> `gemini-flash-latest` -> `gemini-2.5-pro`).
- **Zamanlayıcı (Scheduler):** `cron-job.org` üzerinden dakik tetikleme modeli (GitHub Actions dahili gecikmeli cron'ları kaldırıldı).
- **Eşleşme Motoru:** `C#` / Unity oyun ilanlarının `C` diliyle çakışması kesin olarak engellendi; .NET, iOS, Flutter gibi alan dışı ilanlar filtrelendi.
- **Birim Testler:** 15 testin tamamı (%100) başarıyla geçmektedir.

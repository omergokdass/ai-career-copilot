# LinkedIn Job Agent & Autonomous AI Application Pipeline
## Sistem Durumu ve Mevcut Aşama (El Sıkışma Dosyası)

Bu dosya, projenin mevcut teknik durumunu, doğrulanmış mimari kararları ve objektif çalışma sınırlarını özetler.

---

### 1. Aday Profili (Tek Gerçeklik Kaynağı - %100 Doğrulanmış)
- **Aday:** Ömer Faruk Gökdaş (İstanbul)
- **Eğitim:**
  - Nişantaşı Üniversitesi - Yazılım Mühendisliği Lisans Mezuniyeti (**Eylül 2021 - Temmuz 2026**)
  - 42 İstanbul (Ecole 42) - Sistem Programlama ve Yazılım Mühendisliği (**Ocak 2025 - Devam Ediyor**)
- **İhbar Süresi:** 0 Gün (Hemen Başlayabilir)
- **Doğrulanmış Projeler:**
  - `branda.ist`: 80+ sayfalık canlı ticari web platformu (Astro, TypeScript, SSG, Sharp, PurgeCSS, Programatik SEO)
  - `Minishell & Philosophers` (42 Istanbul): POSIX Unix shell, process control, pipes, Valgrind sızıntısız bellek yönetimi, multithreading & mutex.
  - `NishChat` (Bitirme Projesi): Node.js, Express, Socket.IO, PostgreSQL gerçek zamanlı mesajlaşma platformu.
  - `Beşiktaş Belediyesi Stajı`: Active Directory, TCP/IP, kurumsal IT desteği, Bash otomasyonu.
- **Kesin Kural:** Asla uydurma teknoloji (Spring Boot 3, Redis, Couple OS vb.) eklenemez.

---

### 2. Başvuru ve Dil Kuralları
- **CV Dosyası (Sabit Kural):** İlan Türkçe de olsa İngilizce de olsa **HER ZAMAN 92 puanlık İngilizce Master ATS CV** kullanılır:
  `source_resume/Omer_Faruk_Gokdas_CV_Master_ATS.pdf`
- **Ön Yazı (Cover Letter) Dili:**
  - İlan Türkçe ise: Kurumsal ve akıcı **Türkçe Ön Yazı**.
  - İlan İngilizce ise: Şirket odaklı profesyonel **İngilizce Cover Letter**.
- **İki Kademeli Triage:**
  - `%70+`: Güçlü Eşleşme (`STRONG` / `RECOMMENDED`)
  - `%50 - %69`: Sınırda / Denenebilir İlan (`BORDERLINE` - "Bunları da deneyebilirsin")
  - `<%50`: Elendi (`SKIP`)

---

### 3. Aktif Entegrasyonlar ve Tamamlanan Düzeltmeler
- **Google Gemini API Entegrasyonu (`core/ai_reviewer.py`):**
  - Google Generative AI REST API üzerinden `gemini-2.5-flash` (ve `gemini-1.5-flash` fallback) modeli bağlandı.
  - JSON formatında yapılandırılmış çıktı ile semantik eşleşme skoru, karar gerekçesi ve her şirkete özel %100 özgün ön yazı üretimi sağlandı.
  - API anahtarı girilmediğinde veya ağ kesintilerinde sistemin aksamaması için deterministik kural motoru devrede tutuldu.
- **Güvenlik ve Gizlilik:**
  - Telegram bot token ve Gemini API anahtarları `.env` ve GitHub Secrets üzerinden yönetilecek şekilde refactor edildi; `notifications.yaml` içindeki açık token temizlendi.
- **Veritabanı ve Bildirim Düzeltmeleri:**
  - `core/db.py` SQLite bağlantı sızıntısı giderildi (`contextmanager` ile otomatik kapanma sağlandı).
  - `core/notifier.py` günlük özet istatistiklerindeki sözlük anahtarı hatası (`applied_auto` -> `applied_auto_count`) düzeltildi.
  - `core/bot_apply.py` içindeki `company` NameError hatası giderildi.
- **GitHub Actions:**
  - `.github/workflows/daily_pipeline.yml` her gün Türkiye saatiyle **10:00'da** otomatik çalışacak şekilde ayarlandı.
  - Playwright Chromium ve environment secret enjeksiyonu modernize edildi.
- **Birim Testler:**
  - `tests/test_system.py` altındaki 10 birim testin tamamı (%100) başarıyla geçmektedir (`OK`).

---

### 4. Operasyonel Gerçekler ve Riskler
- **LinkedIn Başvuru Süreci:**
  - GitHub Actions gibi bulut CI/CD sunucularında doğrudan LinkedIn'e headless başvuru göndermek, LinkedIn'in Cloudflare/IP bot bariyerine ve 2FA kontrolüne takılır; ayrıca hesabın askıya alınma riski vardır.
  - Bu sebeple sistem: İlanları tarar, Gemini ile analiz eder, adaya özel 92 puanlık Master ATS CV ve özgün Cover Letter'ı hazırlar, doğrudan Telegram'a tek tıkla başvuru linkiyle birlikte bilgi kartı olarak iletir.
  - Yerel makinede `login_linkedin.py` ile oturum açıldığında `core/bot_apply.py` destekli başvuru için altyapı hazırdır.

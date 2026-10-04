import os
import re
import json
import time
import yaml
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"

class AIReviewer:
    """
    Ömer Faruk Gökdaş'ın gerçek 42 Istanbul, Yazılım Mühendisliği bitirme projesi ve
    Beşiktaş Belediyesi staj deneyimini temel alan; mülakatta arkasında duramayacağı
    hiçbir sahte teknoloji veya şişirilmiş rakam barındırmayan %100 dürüst yapay zeka analiz motoru.
    
    Google Gemini API entegrasyonu ile ilanları derinlemesine semantik olarak değerlendirir,
    uyum puanı üretir ve her şirkete özel %100 özgün ön yazı hazırlar.
    API anahtarı bulunmadığında veya ağ kesintilerinde deterministik kural motoruna geri döner.
    """
    def __init__(self):
        with open(CONFIG_DIR / "master_profile.yaml", "r", encoding="utf-8") as f:
            self.profile = yaml.safe_load(f)
        with open(CONFIG_DIR / "application_rules.yaml", "r", encoding="utf-8") as f:
            self.rules = yaml.safe_load(f)
            
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
        self.max_api_calls_per_run = int(os.environ.get("MAX_AI_CALLS_PER_RUN", "15"))
        self.api_call_count = 0
        self.consecutive_errors = 0
        self.circuit_broken = False

    def review_job_deeply(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        İlanı derinlemesine inceler:
        1. Eğer GEMINI_API_KEY mevcutsa, kota aşılmamışsa ve devre kesici tetiklenmemişse Google Gemini çağrılır.
        2. Maksimum çağrı sınırına (15) ulaşıldığında veya üst üste 2 hata alındığında API kilitlenir,
           kalan tüm ilanlar 0 maliyetle yerel deterministik kural motoruyla işlenir.
        """
        if self.gemini_api_key and not self.circuit_broken:
            if self.api_call_count >= self.max_api_calls_per_run:
                print(f"[AIReviewer Kota Kilidi] Vardiya başı maksimum AI istek sınırına ({self.max_api_calls_per_run}) ulaşıldı. Kalan ilanlar yerel kural motoruyla (0 maliyet) işlenecek.")
                return self._heuristic_review(job)

            # Kota aşımı (15 RPM) önlemek için istekler arasına 1.5 saniye nezaket gecikmesi
            time.sleep(1.5)
            gemini_result = self._review_with_gemini(job)
            if gemini_result:
                self.api_call_count += 1
                self.consecutive_errors = 0
                return gemini_result
            else:
                self.consecutive_errors += 1
                if self.consecutive_errors >= 2:
                    self.circuit_broken = True
                    print(f"[AIReviewer Devre Kesici] Üst üste {self.consecutive_errors} kez API hatası alındı. Döngüyü ve kotayı korumak için API devre dışı bırakıldı. Kalan ilanlar yerel motorla işlenecek.")

        return self._heuristic_review(job)

    def _call_gemini_api(self, prompt: str, model_name: Optional[str] = None) -> Optional[str]:
        """Google Generative Language REST API üzerinden Gemini modelini çağırır."""
        model = model_name or self.gemini_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                candidates = resp_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except urllib.error.HTTPError as e:
            # Rate limit (429) durumunda bekle ve bir kez daha dene
            if e.code == 429:
                print(f"[AIReviewer] Gemini API Kota Limiti (429). 6 saniye beklenip tekrar deneniyor...")
                time.sleep(6)
                try:
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        resp_json = json.loads(resp.read().decode("utf-8"))
                        candidates = resp_json.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "")
                except Exception as retry_err:
                    print(f"[AIReviewer] Gemini API Retry Hatası: {retry_err}")
            # Model bulunamadıysa (404) sırayla fallback modelleri dene
            elif e.code == 404:
                fallbacks = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash"]
                for fb in fallbacks:
                    if fb != model:
                        return self._call_gemini_api(prompt, model_name=fb)
            print(f"[AIReviewer] Gemini API HTTP Hatası ({e.code}): {e.reason}")
        except Exception as e:
            print(f"[AIReviewer] Gemini API Bağlantı Hatası: {e}")
            
        return None

    def _review_with_gemini(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Gemini LLM modeline ilanın tamamını ve aday profilini vererek derin semantik analiz alır."""
        title = job.get("title", "")
        company = job.get("company", "Company")
        desc = job.get("description", "")
        is_easy_apply = job.get("is_easy_apply", False)
        
        master_cv_rel = self.profile["personal"].get("master_cv_en_pdf", "source_resume/Omer_Faruk_Gokdas_CV_Master_ATS.pdf")
        recommended_cv_pdf = str(BASE_DIR / master_cv_rel)
        
        candidate_info = f"""
Aday: Ömer Faruk Gökdaş (İstanbul, Türkiye)
İletişim: {self.profile['personal']['email']} | {self.profile['personal']['phone']}
LinkedIn: {self.profile['personal']['linkedin']} | GitHub: {self.profile['personal']['github']}
Eğitim:
- Nişantaşı Üniversitesi, Yazılım Mühendisliği Lisans Mezuniyeti (Eylül 2021 - Temmuz 2026)
- 42 İstanbul (Ecole 42), Sistem Programlama ve Yazılım Mühendisliği (Ocak 2025 - Devam Ediyor)
İhbar Süresi: 0 Gün (Hemen Başlayabilir)
Doğrulanmış Gerçek Projeler (%100 Tek Gerçeklik Kaynağı):
1. CoupleOS: React Native (Expo), TypeScript, NestJS, Prisma ORM, Socket.IO, Supabase PostgreSQL, Zustand, Shopify Skia. Çiftler için gerçek zamanlı mobil uygulama ve backend mimarisi. Google Gemini & OpenAI API'leri ile çoklu LLM entegrasyonu, hata toleranslı fallback mekanizmaları, canlı tuval çizimi ve anlık mesajlaşma.
2. branda.ist: Astro, TypeScript, SSG, Sharp, PurgeCSS ile 80+ sayfalık canlı ticari platform, 1.5s altı yükleme, programatik SEO.
3. Minishell & Philosophers (42 Istanbul): C, POSIX Unix sistem çağrıları, fork/pipe/dup2, Valgrind sızıntısız bellek yönetimi, multithreading & mutex senkronizasyonu.
4. NishChat (Üniversite Bitirme Projesi): Node.js, Express, Socket.IO, PostgreSQL ile gerçek zamanlı çift yönlü mesajlaşma.
5. Beşiktaş Belediyesi IT Stajı: Active Directory, TCP/IP ağ yönetimi, donanım/işletim sistemi desteği, Bash otomasyon betikleri.
KESİN KURAL: Adayın yapmadığı hiçbir sahte teknoloji (Spring Boot 3, Redis, AWS, Kubernetes, Flutter, Swift vb.) uydurulamaz. Yalnızca yukarıdaki doğrulanmış gerçek yetenekler ve projeler temel alınmalıdır.
"""

        cover_letter_instruction = ""
        if is_easy_apply:
            cover_letter_instruction = """
4. LINKEDIN KOLAY BAŞVURU MESAJI (Top Choice - Why this job is a top choice and why you're a good fit):
   - LinkedIn mobil uygulamasındaki 'Include a message with your application (0/400)' kutusu için doğrudan bir başvuru mesajı hazırla.
   - KESİNLİKLE MAKSİMUM 400 KARAKTER (boşluklar dahil) olmalıdır! (İdeal aralık: 240 - 360 karakter).
   - ASLA RESMİ MEKTUP / E-POSTA ŞABLONU KULLANMA:
     * 'Sayın X İşe Alım Ekibi', 'Dear Hiring Team' gibi hitaplar YAZMA (karakter israfıdır).
     * 'Saygılarımla', 'Ömer Faruk Gökdaş', telefon, e-posta gibi imza blokları YAZMA (LinkedIn profiliniz zaten ekranda adayın adıyla birlikte görünmektedir).
   - YAPAY ZEKA KLİŞELERİ KULLANMA: 'Büyük bir heyecanla başvuruyorum', 'Mükemmel bir uyum içerisindeyim' gibi robotik laflardan kaçın.
   - DOĞRUDAN VE NET İKİ ŞEYİ ANLAT:
     1. Bu rol/şirket neden birinci tercihin? (İlandaki spesifik problem, teknoloji veya alan).
     2. Adayın hangi somut doğrulanmış projesi (CoupleOS'ta LLM/NestJS/React Native, 42 Minishell'de C/Unix/bellek yönetimi, branda.ist'te Astro/TS/SEO) bu ilanın ihtiyacına doğrudan hız kazandıracak?
   - Üslup: Mühendisten mühendise, kendinden emin, samimi ve %100 doğal. İlan Türkçe ise Türkçe, İngilizce ise İngilizce.
   - 'custom_cover_letter' alanına SADECE bu mesaj metnini yaz.
"""
        else:
            cover_letter_instruction = """
4. BAŞVURU MESAJI KURALI (Şirket Portalı / Dış Başvuru):
   - Bu bir şirket portalı dış başvurusudur (Easy Apply DEĞİLDİR).
   - KESİNLİKLE mesaj oluşturma. 'custom_cover_letter' alanını BOŞ STRING ("") olarak bırak.
"""

        prompt = f"""
Sen iş başvurularını titizlikle değerlendiren kıdemli bir teknik direktörsün.
Aşağıda verilen aday profilini ve iş ilanının TAMAMINI incele:

{candidate_info}

İNCELENECEK İŞ İLANI:
- Şirket: {company}
- Pozisyon: {title}
- Başvuru Kanalı: {'LinkedIn Kolay Başvuru (Easy Apply)' if is_easy_apply else 'Şirket Portalı / Dış Başvuru'}
- İlan Metninin Tamamı (Hakkında, Görevler ve Gereksinimler):
{desc[:6000]}

GÖREVLERİN:
1. İlan dilini ('tr' veya 'en') belirle.
2. Pozisyonun gerçek alanını ve adayın yetenekleriyle uyumunu değerlendir:
   - DİKKAT: Pozisyon yazılım, sistem, bilişim veya yapay zeka alanı DIŞINDA ise (örn: Hukuk, Kimya, Tıp, Eczacılık, Satış, Pazarlama, Muhasebe, İnşaat, Makine vb.) KESİNLİKLE verdict='SKIP', match_score=0.0 ver.
   - Yazılım teknolojileri adayın alanıyla tamamen alakasızsa (.NET/C#, Flutter, Swift/iOS Native, SAP): verdict='SKIP', match_score < 50.
   - İlanda kıdemli yazsa bile adayın C/C++, Sistem, Backend (Nest/Node/SQL), Mobil (React Native), Web (Astro/TS) veya AI altyapısı örtüşüyorsa: verdict='BORDERLINE', match_score 50-69.
   - İlan staj, genç yetenek, junior, mezun veya adayın ana teknolojileriyle doğrudan örtüşüyorsa: verdict='RECOMMENDED', match_score >= 70.
3. İlan için en uygun öne çıkarılacak projeyi seç (CoupleOS, branda.ist, Minishell & Philosophers, NishChat veya Beşiktaş BT Stajı).
{cover_letter_instruction}

Lütfen çıktıyı SADECE geçerli bir JSON nesnesi olarak şu şemada döndür:
{{
  "verdict": "RECOMMENDED" | "BORDERLINE" | "SKIP",
  "match_score": 75.0,
  "language": "tr" | "en",
  "highlighted_project": "Seçilen projenin adı",
  "reasoning": "Neden bu kararın verildiğini açıklayan 1-2 cümlelik Türkçe veya İngilizce özet",
  "custom_cover_letter": ""
}}
"""
        response_text = self._call_gemini_api(prompt)
        if not response_text:
            return None
            
        try:
            # Markdown code fences temizliği (```json ... ```)
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            
            data = json.loads(cleaned)
            verdict = data.get("verdict", "RECOMMENDED").upper()
            if verdict not in ("RECOMMENDED", "BORDERLINE", "SKIP"):
                verdict = "RECOMMENDED"

            custom_cover_letter = str(data.get("custom_cover_letter", "")).strip()
            # 400 Karakter Easy Apply Garantisi
            if is_easy_apply and custom_cover_letter:
                if len(custom_cover_letter) > 400:
                    custom_cover_letter = custom_cover_letter[:396].rsplit(" ", 1)[0] + "..."
            elif not is_easy_apply:
                custom_cover_letter = ""
                
            return {
                "verdict": verdict,
                "language": data.get("language", self._detect_language(title + " " + desc)),
                "match_score": float(data.get("match_score", 70.0)),
                "reasoning": str(data.get("reasoning", "Gemini AI analizi tamamlandı.")),
                "highlighted_project": str(data.get("highlighted_project", "42 Istanbul & branda.ist")),
                "recommended_cv_pdf": recommended_cv_pdf,
                "custom_cover_letter": custom_cover_letter,
                "ai_source": "Google Gemini"
            }
        except Exception as e:
            print(f"[AIReviewer] Gemini yanıtı JSON olarak ayrıştırılamadı: {e}")
            return None

    def _heuristic_review(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministik ve yedek kural tabanlı inceleme motoru."""
        title = job.get("title", "")
        company = job.get("company", "Company")
        desc = job.get("description", "")
        is_easy_apply = job.get("is_easy_apply", False)
        desc_lower = desc.lower()
        title_lower = title.lower()

        # 1. Alakasız pozisyon filtrelemesi (.NET, C#, iOS, Flutter, SAP vb.)
        irrelevant_keywords = [".net", "c#", "flutter", "ios developer", "android developer", "ui/ux designer", "sap ", "sales", "recruiter", "accountant"]
        software_keywords = ["c++", "c ", "systems", "backend", "frontend", "web", "software", "developer", "mühendis", "yazılım"]
        if any(irr in title_lower for irr in irrelevant_keywords) and not any(k in title_lower for k in software_keywords):
            return {
                "verdict": "SKIP",
                "match_score": 35.0,
                "reasoning": f"Pozisyon adayın gerçek yetenek havuzu dışındaki alanda: '{title}'",
                "custom_cover_letter": "",
                "language": "tr" if "tr" == self._detect_language(title + " " + desc) else "en",
                "recommended_cv_pdf": str(BASE_DIR / self.profile["personal"].get("master_cv_en_pdf", "source_resume/Omer_Faruk_Gokdas_CV_Master_ATS.pdf")),
                "highlighted_project": "",
                "ai_source": "Heuristic Rules"
            }

        # 2. İlan Dilini Belirle (Türkçe vs İngilizce)
        lang = self._detect_language(title + " " + desc)

        # 3. Şirketin ve Pozisyonun Ana Odağını Belirle
        is_mobile_or_ai = any(k in desc_lower or k in title_lower for k in [
            "react native", "mobile", "mobil", "expo", "ios", "android", "ai", "yapay zeka", "llm", "prompt", "machine learning", "generative ai"
        ])
        is_systems_cpp = any(k in desc_lower or k in title_lower for k in [
            "c++", "c developer", "embedded", "systems", "posix", "linux", "kernel", "low level", "gömülü", "network", "security"
        ])
        is_backend_node = any(k in desc_lower or k in title_lower for k in [
            "nest", "node", "express", "backend", "back-end", "socket", "api", "database", "sql", "postgresql", "prisma"
        ])
        is_frontend_web = any(k in desc_lower or k in title_lower for k in [
            "frontend", "front-end", "web developer", "astro", "typescript", "javascript", "react", "html", "css", "ui developer", "web geliştirici"
        ])
        is_it_support = any(k in desc_lower or k in title_lower for k in [
            "it support", "destek", "sistem uzman", "active directory", "help desk", "sistem yöneticisi", "ağ ve sistem"
        ])
        is_intern_talent = any(k in desc_lower or k in title_lower for k in [
            "staj", "intern", "trainee", "genç yetenek", "talent program", "graduate", "new grad", "yeni mezun"
        ])

        candidate_name = self.profile["personal"]["full_name"].title()
        phone = self.profile["personal"]["phone"]
        email = self.profile["personal"]["email"]
        linkedin = self.profile["personal"]["linkedin"]
        github = self.profile["personal"]["github"]

        master_cv_rel = self.profile["personal"].get("master_cv_en_pdf", "source_resume/Omer_Faruk_Gokdas_CV_Master_ATS.pdf")
        recommended_cv_pdf = str(BASE_DIR / master_cv_rel)

        match_score = float(job.get("match_score", 75.0))
        missing_skills = job.get("missing_skills", [])
        is_borderline = (50.0 <= match_score < 70.0)

        if lang == "tr":
            if is_mobile_or_ai:
                project_story = "Geliştirdiğim CoupleOS projesinde React Native (Expo) ve NestJS mimarisi üzerinde çiftler için uçtan uca gerçek zamanlı bir mobil uygulama inşa ettim. Bu süreçte Zustand ile durum yönetimini kurarken, Socket.IO ile canlı veri senkronizasyonu sağladım ve Google Gemini ile OpenAI API'lerini entegre ederek hata toleranslı çoklu yapay zeka (LLM) veri akışları kurguladım."
                best_project = "CoupleOS (Mobil & Çoklu LLM Mimarisi)"
            elif is_systems_cpp:
                project_story = "42 Istanbul'un zorlu ve test odaklı sistem programlama eğitimi kapsamında Valgrind ile doğrulanmış, bellek sızıntısız Minishell Unix kabuğunu (POSIX sistem çağrıları, pipe, fork, sinyal yönetimi) ve POSIX mutex senkronizasyonlu Dining Philosophers eşzamanlılık projelerini geliştirdim."
                best_project = "Minishell & Philosophers (42 Istanbul)"
            elif is_backend_node:
                project_story = "Backend geliştirmede NestJS, Node.js ve PostgreSQL üzerinde ölçeklenebilir REST servisleri ve Socket.IO tabanlı gerçek zamanlı veri akışları tasarladım. CoupleOS ve NishChat projelerimde Prisma ORM ile ilişkisel veri modellemesi ve JWT kimlik doğrulama mimarilerini başarıyla uyguladım."
                best_project = "CoupleOS & NishChat (Backend & Veritabanı)"
            elif is_frontend_web:
                project_story = "Astro ve TypeScript kullanarak 80'den fazla sayfadan oluşan ticari branda.ist platformunu hayata geçirdim; Sharp ve PurgeCSS optimizasyonlarıyla sayfa yükleme sürelerini 1.5 saniyenin altına indirirken programatik SEO altyapısını inşa ettim."
                best_project = "branda.ist (Ticari Web Platformu — Astro & TypeScript)"
            elif is_it_support:
                project_story = "Beşiktaş Belediyesi Bilgi İşlem Müdürlüğü stajımda 500'den fazla iş istasyonunda Active Directory yönetimi, TCP/IP ağ sorun giderme ve rutin operasyonların otomasyonu için Bash betikleri geliştirdim."
                best_project = "BT Stajı (Beşiktaş Belediyesi)"
            else:
                project_story = "Nişantaşı Üniversitesi Yazılım Mühendisliği teorik altyapımı 42 İstanbul'un zorlu peer-to-peer sistem geliştirme pratiğiyle birleştirerek sağlam algoritmik düşünme, temiz kod mimarisi ve sıfır harici kütüphane bağımlılığıyla problem çözme kabiliyeti edindim."
                best_project = "42 Istanbul & Yazılım Mühendisliği Eğitimi"

            if is_intern_talent:
                p1 = f"Şirketiniz {company} bünyesinde açık bulunan {title} pozisyonuna başvurmaktan büyük memnuniyet duyuyorum. Nişantaşı Üniversitesi Yazılım Mühendisliği bölümünden Temmuz 2026'da mezun oldum ve eş zamanlı olarak 42 İstanbul sistem programlama eğitimime aktif biçimde devam etmekteyim."
            else:
                p1 = f"Şirketiniz {company} bünyesinde yer alan {title} pozisyonu için başvurumu iletmek isterim. Yazılım Mühendisliği lisans mezuniyetim ve 42 İstanbul sistem programlama eğitimim süresince edindiğim mühendislik disipliniyle ekibinize somut katkı sunmayı hedefliyorum."

            p2 = f"Eğitim ve proje süreçlerimde yüzeysel yaklaşımlar yerine mühendislik derinliğine, performans odaklı mimarilere ve temiz problem çözme disiplinine öncelik verdim. {project_story}"
            p3 = f"Herhangi bir ihbar sürem (0 gün) bulunmamakta olup, ekibinize tam zamanlı olarak hemen katılabilirim. {company} ekibinin mühendislik hedefleri doğrultusunda sorumluluk almaktan heyecan duyuyorum. Detaylı özgeçmişim ekte yer almakta olup, niteliklerimi bir mülakatta aktarmaktan mutluluk duyarım."

            if is_easy_apply:
                if is_mobile_or_ai:
                    custom_cover_letter = f"CoupleOS projemde React Native ve NestJS üzerinde çoklu LLM (Gemini/OpenAI) entegrasyonu ve gerçek zamanlı mimari kurdum. {company}'ın bu alandaki hedefleri tam olarak odaklandığım mühendislik derinliğiyle örtüşüyor. 42 İstanbul sistem disiplinimle ekibinize hemen adapte olabilirim."
                elif is_systems_cpp:
                    custom_cover_letter = f"42 Istanbul'da C ile POSIX Unix Minishell ve mutex senkronizasyonlu multithread sistemler geliştirdim. {company}'ın düşük seviye sistem altyapısı mühendislik temellerimle birebir uyuşuyor. Sıfır ihbar süresiyle ekibinize hemen değer katabilirim."
                elif is_frontend_web:
                    custom_cover_letter = f"Astro ve TypeScript ile 80+ sayfalık canlı branda.ist platformunu sub-1.5s hız ve SEO optimizasyonuyla yayına aldım. {company}'ın modern web ve kullanıcı deneyimi standartlarına ilk günden somut katkı sunmaya hazırım."
                elif is_backend_node:
                    custom_cover_letter = f"NestJS, Node.js ve PostgreSQL üzerinde ilişkisel veri modelleme ve Socket.IO canlı veri akışları inşa ettim. {company} backend hedefleriniz için temiz ve ölçeklenebilir mimari üretmeye hazırım."
                else:
                    custom_cover_letter = f"42 İstanbul'un derin sistem programlama ve algoritmik problem çözme disipliniyle yetiştim. {company}'ın mühendislik hedefleri üzerinde çalışmak istediğim alanla birebir örtüşüyor. Tam zamanlı olarak hemen başlayabilirim."
                if len(custom_cover_letter) > 400:
                    custom_cover_letter = custom_cover_letter[:396].rsplit(" ", 1)[0] + "..."
            else:
                custom_cover_letter = ""

            if is_borderline:
                reasoning = f"İlan {company} - {title} (Türkçe). Düşük ihtimal / sınırda eşleşme (%{match_score:.1f}). İlanda geçen ekler ({', '.join(missing_skills[:3]) if missing_skills else 'Ek deneyim'}) bulunuyor; temel yazılım birikimiyle denenebilir."
            else:
                reasoning = f"İlan {company} - {title} (Türkçe). Güçlü eşleşme (%{match_score:.1f}). Adayın gerçek {best_project} deneyimi ve doğrulanmış yetenekleriyle örtüşüyor."

        else:
            # English
            if is_mobile_or_ai:
                best_project = "CoupleOS (Mobile & Multi-LLM Architecture)"
            elif is_systems_cpp:
                best_project = "Minishell & Philosophers (42 Istanbul)"
            elif is_backend_node:
                best_project = "CoupleOS & NishChat (Backend & Real-Time APIs)"
            elif is_frontend_web:
                best_project = "branda.ist (Commercial Web Platform — Astro & TypeScript)"
            elif is_it_support:
                best_project = "IT Internship (Besiktas Municipality)"
            else:
                best_project = "42 Istanbul & Software Engineering Foundations"

            if is_easy_apply:
                if is_mobile_or_ai:
                    custom_cover_letter = f"In CoupleOS, I architected production multi-LLM pipelines with OpenAI/Gemini and NestJS/React Native. {company}'s vision aligns directly with my engineering focus. Available immediately with zero notice period."
                elif is_systems_cpp:
                    custom_cover_letter = f"At 42 Istanbul, I built Unix process pipelines and multithreaded mutex concurrency in C from scratch. {company}'s low-level systems focus matches my core strengths. Ready to contribute immediately."
                elif is_frontend_web:
                    custom_cover_letter = f"I deployed branda.ist using Astro and TypeScript with sub-1.5s load times and automated SEO. {company}'s frontend standards strongly resonate with my clean code and web performance focus."
                else:
                    custom_cover_letter = f"With a Software Engineering degree and rigorous systems training from 42 Istanbul, I thrive on solving complex technical challenges. Eager to contribute to {company}'s engineering objectives immediately."
                if len(custom_cover_letter) > 400:
                    custom_cover_letter = custom_cover_letter[:396].rsplit(" ", 1)[0] + "..."
            else:
                custom_cover_letter = ""

            if is_borderline:
                reasoning = f"İlan {company} - {title} (English). Borderline match (%{match_score:.1f}). Some preferred technologies ({', '.join(missing_skills[:3]) if missing_skills else 'Senior requirements'}) are stretch goals; worth trying based on strong core engineering foundations."
            else:
                reasoning = f"İlan {company} - {title} (English). Strong match (%{match_score:.1f}). Matches real {best_project} experience and verified technical skills."

        verdict = "BORDERLINE" if is_borderline else "RECOMMENDED"

        return {
            "verdict": verdict,
            "language": lang,
            "match_score": match_score,
            "reasoning": reasoning,
            "highlighted_project": best_project,
            "recommended_cv_pdf": recommended_cv_pdf,
            "custom_cover_letter": custom_cover_letter.strip(),
            "ai_source": "Heuristic Rules"
        }

    def _detect_language(self, text: str) -> str:
        """İlan metninin Türkçe mi yoksa İngilizce mi olduğunu analiz eder."""
        text_lower = text.lower()
        tr_chars = set("çğıöşüÇĞİÖŞÜ")
        tr_char_count = sum(1 for c in text if c in tr_chars)

        tr_words = [
            "aranan", "nitelikler", "iş tanımı", "tecrübe", "mezun", "başvuru",
            "yetkinlikler", "adaylar", "tercihen", "sorumluluklar", "çalışma",
            "şirketimizde", "bölümlerinden", "yetenek", "pozisyon", "departmanı"
        ]
        tr_word_count = sum(1 for w in tr_words if re.search(r'\b' + re.escape(w) + r'\b', text_lower))

        if tr_char_count >= 3 or tr_word_count >= 2:
            return "tr"
        return "en"

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

    def review_job_deeply(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        İlanı derinlemesine inceler:
        1. Eğer GEMINI_API_KEY mevcutsa Google Gemini LLM ile analiz eder.
        2. Anahtar yoksa veya API çağrısı başarısız olursa kural tabanlı motoru çalıştırır.
        """
        if self.gemini_api_key:
            gemini_result = self._review_with_gemini(job)
            if gemini_result:
                return gemini_result

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
        """Gemini LLM modeline ilanı ve aday profilini vererek JSON formatında analiz alır."""
        title = job.get("title", "")
        company = job.get("company", "Company")
        desc = job.get("description", "")
        
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

        prompt = f"""
Sen iş başvurularını değerlendiren uzman ve dürüst bir teknik kariyer danışmanısın.
Aşağıda verilen aday profilini ve iş ilanını detaylı incele:

{candidate_info}

İNCELENECEK İŞ İLANI:
- Şirket: {company}
- Pozisyon: {title}
- İlan Açıklaması: {desc[:2500]}

GÖREVLERİN:
1. İlan dilini ('tr' veya 'en') belirle.
2. Pozisyonun adayın yetenekleriyle uyumunu değerlendir.
   - İlan tamamen alakasız bir alandaysa (örn: Flutter, Swift/iOS native, .NET/C#, SAP, Satış, Muhasebe) veya uyumsuzsa: verdict='SKIP', match_score < 50.
   - İlanda 3+ yıl veya kıdemli yazsa bile adayın C/C++, Sistem, Backend (Nest/Node/SQL), Mobil (React Native) veya Frontend (Astro/TS) temelleri örtüşüyorsa: verdict='BORDERLINE', match_score 50-69.
   - İlan staj, genç yetenek, junior, mezun veya adayın ana teknolojileriyle doğrudan örtüşüyorsa: verdict='RECOMMENDED', match_score >= 70.
3. İlan için en uygun öne çıkarılacak projeyi seç (CoupleOS, branda.ist, Minishell & Philosophers, NishChat veya Beşiktaş BT Stajı).
4. Bu şirkete ve pozisyona özel, ASLA YAPAY ZEKA ŞABLONU GİBİ DURMAYAN, samimi, akıcı ve profesyonel bir Ön Yazı (Cover Letter) yaz:
   - KESİNLİKLE MADDE İŞARETİ VEYA LİSTE (- **...**) KULLANMA. Tamamen akıcı 3 doğal paragraftan oluşsun:
     * 1. Paragraf: Pozisyona özel doğrudan giriş, Yazılım Mühendisliği mezuniyeti ve 42 İstanbul altyapısı.
     * 2. Paragraf: Pozisyonun gereksinimlerine göre adayın en uygun projesindeki (CoupleOS, branda.ist veya 42 Minishell) somut mühendislik meydan okumasını ve çözümünü anlatan doğal bir paragraf.
     * 3. Paragraf: İhbar süresinin bulunmadığını (0 gün - hemen başlayabilir), şirketin ekibine katılma motivasyonunu belirten profesyonel ve saygılı kapanış.
   - İlan Türkçe ise Türkçe, İngilizce ise İngilizce yaz.
   - Hitap: "Sayın {company} İşe Alım Ekibi," (TR) veya "Dear Hiring Team at {company}," (EN).
   - İmza: Ömer Faruk Gökdaş ve iletişim bilgileri.

Lütfen çıktıyı SADECE geçerli bir JSON nesnesi olarak şu şemada döndür:
{{
  "verdict": "RECOMMENDED" | "BORDERLINE" | "SKIP",
  "match_score": 75.0,
  "language": "tr" | "en",
  "highlighted_project": "Seçilen projenin adı",
  "reasoning": "Neden bu kararın verildiğini açıklayan 1-2 cümlelik Türkçe veya İngilizce özet",
  "custom_cover_letter": "Hazırlanan tam metin 3 paragraflık akıcı ön yazı"
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
                
            return {
                "verdict": verdict,
                "language": data.get("language", self._detect_language(title + " " + desc)),
                "match_score": float(data.get("match_score", 70.0)),
                "reasoning": str(data.get("reasoning", "Gemini AI analizi tamamlandı.")),
                "highlighted_project": str(data.get("highlighted_project", "42 Istanbul & branda.ist")),
                "recommended_cv_pdf": recommended_cv_pdf,
                "custom_cover_letter": str(data.get("custom_cover_letter", "")).strip(),
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

            custom_cover_letter = f"""Sayın {company} İşe Alım Ekibi,

{p1}

{p2}

{p3}

Saygılarımla,

{candidate_name}
{phone} | {email}
{linkedin} | {github}"""

            if is_borderline:
                reasoning = f"İlan {company} - {title} (Türkçe). Düşük ihtimal / sınırda eşleşme (%{match_score:.1f}). İlanda geçen ekler ({', '.join(missing_skills[:3]) if missing_skills else 'Ek deneyim'}) bulunuyor; temel yazılım birikimiyle denenebilir."
            else:
                reasoning = f"İlan {company} - {title} (Türkçe). Güçlü eşleşme (%{match_score:.1f}). Adayın gerçek {best_project} deneyimi ve doğrulanmış yetenekleriyle örtüşüyor."

        else:
            # English
            if is_mobile_or_ai:
                project_story = "In my flagship project CoupleOS, I architected a full-stack real-time mobile platform utilizing React Native (Expo) with Zustand on the frontend and NestJS with Prisma and Supabase PostgreSQL on the backend. I integrated multi-LLM pipelines combining Google Gemini and OpenAI APIs with graceful fallback mechanisms, alongside WebSocket-driven event streaming via Socket.IO."
                best_project = "CoupleOS (Mobile & Multi-LLM Architecture)"
            elif is_systems_cpp:
                project_story = "Through the rigorous, test-driven curriculum at 42 Istanbul, I developed a strong foundation in low-level systems programming in C. My work includes Minishell (a POSIX-compliant Unix shell with process control, pipes, and Valgrind-verified zero-leak memory management) and multithreaded concurrency solutions using POSIX mutex synchronization in Dining Philosophers."
                best_project = "Minishell & Philosophers (42 Istanbul)"
            elif is_backend_node:
                project_story = "On the backend, I design reliable REST services and real-time architectures using NestJS, Node.js, and PostgreSQL. In CoupleOS and NishChat, I implemented Prisma ORM relational modeling, JWT authentication, and bidirectional WebSocket communication with Socket.IO, prioritizing clean code architecture and data consistency."
                best_project = "CoupleOS & NishChat (Backend & Real-Time APIs)"
            elif is_frontend_web:
                project_story = "I architected and published branda.ist, an 80+ page production commercial web platform utilizing Astro and TypeScript. By implementing automated component pipelines and optimizing assets with Sharp and PurgeCSS, I achieved sub-1.5s initial page load times alongside structured programmatic SEO."
                best_project = "branda.ist (Commercial Web Platform — Astro & TypeScript)"
            elif is_it_support:
                project_story = "During my IT internship at Besiktas Municipality, I gained hands-on experience maintaining enterprise infrastructure across 500+ workstations, managing Active Directory user credentials, diagnosing TCP/IP network issues, and authoring Bash automation scripts for system diagnostics."
                best_project = "IT Internship (Besiktas Municipality)"
            else:
                project_story = "Combining my Bachelor's degree in Software Engineering from Nisantasi University with the intensive peer-to-peer curriculum at 42 Istanbul, I have developed strong algorithmic foundations, low-level problem-solving abilities, and practical full-stack development experience."
                best_project = "42 Istanbul & Software Engineering Foundations"

            if is_intern_talent:
                p1 = f"I am writing to express my strong interest in the {title} opportunity at {company}. Having graduated with a Bachelor's degree in Software Engineering from Nisantasi University (July 2026) while actively pursuing the rigorous 42 Istanbul systems programming curriculum, I am eager to contribute my technical foundation to your team."
            else:
                p1 = f"I am writing to apply for the {title} position at {company}. With a solid foundation in Software Engineering and rigorous systems programming training from 42 Istanbul, I look forward to contributing dependable, clean code to your engineering objectives."

            p2 = f"Throughout my academic and independent project work, I have focused on genuine engineering depth, performance optimization, and robust problem solving. {project_story}"
            p3 = f"I am currently available to join your team immediately on a full-time basis, with no notice period (0 days). What excites me about {company} is the opportunity to tackle meaningful engineering challenges alongside experienced peers. Thank you for your time and consideration, and I welcome the opportunity to discuss my qualifications in an interview."

            custom_cover_letter = f"""Dear Hiring Team at {company},

{p1}

{p2}

{p3}

Sincerely,

{candidate_name}
{phone} | {email}
{linkedin} | {github}"""

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

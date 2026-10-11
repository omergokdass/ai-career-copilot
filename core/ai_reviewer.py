import os
import json
import yaml
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from core.models import JobPosting, ReviewResult, ReviewVerdict

CONFIG_DIR = Path(__file__).parent.parent / "config"


class AIReviewer:
    """
    Google Gemini bilişsel motoruyla ilanları semantik olarak inceleyen,
    mülakatta savunulabilir %100 dürüst eşleşme puanı ve maksimum 400 karakterlik
    LinkedIn Easy Apply başvuru notu üreten inceleme motoru.
    """

    def __init__(self):
        self.profile = self._load_profile()
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        # Az önce API testiyle doğrulanan modeller
        self.primary_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
        self.fallback_models = ["gemini-3.8-flash", "gemini-flash-latest"]

    def _load_profile(self) -> Dict[str, Any]:
        profile_path = CONFIG_DIR / "candidate_profile.yaml"
        if profile_path.exists():
            with open(profile_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    def review_job(self, job: JobPosting) -> ReviewResult:
        """İlanı Gemini veya deterministik yerel motor ile analiz eder."""
        if self.api_key:
            res = self._review_with_gemini(job)
            if res:
                return res

        # API başarısız olursa yerel deterministik kural motoru devreye girer
        return self._heuristic_review(job)

    def _review_with_gemini(self, job: JobPosting) -> Optional[ReviewResult]:
        """Google Gemini API generateContent endpoint'ini çağırır."""
        prompt = self._build_prompt(job)
        models_to_try = [self.primary_model] + [m for m in self.fallback_models if m != self.primary_model]

        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }

            try:
                resp = requests.post(url, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_json = parts[0].get("text", "{}")
                            parsed = json.loads(raw_json)
                            return self._parse_ai_response(parsed, job)
                elif resp.status_code in (429, 503):
                    time.sleep(2)
                    continue
            except Exception as e:
                print(f"[AIReviewer] Gemini API ({model}) çağrı hatası: {e}")

        return None

    def _build_prompt(self, job: JobPosting) -> str:
        profile_summary = f"""
Aday: Ömer Faruk Gökdaş (Yazılım Mühendisi)
Eğitim:
1. 42 İstanbul (Ecole 42): POSIX Unix, C/C++, Eşzamanlılık (Multithreading/Mutex), Valgrind bellek yönetimi, process/pipe mimarisi.
2. Nişantaşı Üniversitesi: Yazılım Mühendisliği Lisans Mezuniyeti (Temmuz 2026).
Projeler:
- CoupleOS: React Native (Expo), TypeScript, NestJS, Prisma, PostgreSQL, Supabase, Socket.IO, Zustand, Gemini/OpenAI API.
- Minishell & Philosophers: C, POSIX, fork/exec/pipe, pthread mutex eşzamanlılık, Valgrind sıfır sızıntı.
- branda.ist: Canlı 80+ sayfalık web platformu, Astro, TypeScript, SSG, Sharp, SEO.
- NishChat: Bitirme projesi, Node.js, Express, Socket.IO, PostgreSQL gerçek zamanlı mesajlaşma.
- Beşiktaş Belediyesi IT Stajı: Active Directory, TCP/IP, Linux/Bash otomasyonu.
Temel Beceriler: C, C++, TypeScript, JavaScript, Node.js, NestJS, React Native, Astro, PostgreSQL, Linux, Git, Socket.IO.
Bilmediği / Olmayan Beceriler: .NET/C#, Java Spring Boot, Flutter, Swift/iOS Native, SAP, Kubernetes, AWS.
İhbar Süresi: 0 Gün (Hemen Başlayabilir) | Konum: İstanbul
"""
        return f"""
Sen tarafsız ve kıdemli bir Teknik İşe Alım & Yazılım Mühendisliği Uzmanısın.
Aşağıdaki adayın gerçek portföyü ile hedef ilanı karşılaştırarak JSON formatında objektif değerlendirme yap.

[ADAY PROFİLİ]
{profile_summary}

[HEDEF İLAN]
Başlık: {job.title}
Şirket: {job.company}
Lokasyon: {job.location}
Platform: {job.platform}
Kolay Başvuru (Easy Apply): {job.is_easy_apply}
Açıklama:
{job.description[:2500]}

[KURALLAR VE BEKLENEN JSON FORMATI]
{{
  "match_score": float (0.0 - 100.0),
  "verdict": "RECOMMENDED" | "BORDERLINE" | "REJECTED",
  "matched_skills": ["eşleşen yetenekler"],
  "missing_skills": ["adayı zorlayacak eksik yetenekler"],
  "reasoning": "kısa ve net değerlendirme gerekçesi (maksimum 2 cümle)",
  "highlighted_project": "Öne çıkarılacak proje adı (CoupleOS | Minishell | branda.ist | NishChat | BT Stajı)",
  "language": "tr" | "en",
  "easy_apply_note": "LinkedIn Kolay Başvuru mesajı"
}}

ÖNEMLİ KISITLAMALAR:
1. "easy_apply_note" KESİNLİKLE MAKSİMUM 380 KARAKTER OLMALIDIR. Klasik 'Sayın Yetkili' gibi kalıplar kullanma. Adayın 42 İstanbul, bitirme projesi veya CoupleOS tecrübesini şirketin hedefleriyle samimi ve mühendis diliyle bağla.
2. Eğer pozisyon açıkça 5+ yıl tecrübe arayan Kıdemli (Senior/Lead) pozisyon ise veya adayın bilmediği teknolojiler (.NET, Java Spring, SAP, Flutter) zorunlu ise skor 50'nin altında olmalı ve verdict "REJECTED" verilmelidir.
3. Staj, Genç Yetenek veya Junior rollerinde adayın temel C/C++, TypeScript, React Native, NestJS, Linux yetenekleri güçlü eşleşiyorsa skor 65+ ve verdict "RECOMMENDED" verilmelidir.
"""

    def _parse_ai_response(self, data: Dict[str, Any], job: JobPosting) -> ReviewResult:
        score = float(data.get("match_score", 0.0))
        verdict_str = str(data.get("verdict", "REJECTED")).upper()
        
        # Kesin kural: 65 altı asla RECOMMENDED olamaz
        if score < 50.0:
            verdict = ReviewVerdict.REJECTED
        elif score < 65.0:
            verdict = ReviewVerdict.BORDERLINE
        elif verdict_str == "RECOMMENDED":
            verdict = ReviewVerdict.RECOMMENDED
        else:
            verdict = ReviewVerdict.BORDERLINE

        note = str(data.get("easy_apply_note", "")).strip()
        # Kesin 400 karakter garantisi
        if len(note) > 400:
            note = note[:397].rsplit(" ", 1)[0] + "..."

        return ReviewResult(
            match_score=round(score, 1),
            verdict=verdict,
            matched_skills=data.get("matched_skills", []),
            missing_skills=data.get("missing_skills", []),
            reasoning=data.get("reasoning", "Gemini semantik analizi tamamlandı."),
            highlighted_project=data.get("highlighted_project", "CoupleOS & 42 Istanbul"),
            easy_apply_note=note,
            language=data.get("language", "tr")
        )

    def _heuristic_review(self, job: JobPosting) -> ReviewResult:
        """API yokluğunda veya kesintide çalışan deterministik kural motoru."""
        title_l = job.title.lower()
        desc_l = job.description.lower()
        combined = f"{title_l} {desc_l}"

        candidate_tech = [
            ("c++", "C++"), ("c ", "C"), ("typescript", "TypeScript"), ("javascript", "JavaScript"),
            ("node.js", "Node.js"), ("nodejs", "Node.js"), ("nestjs", "NestJS"),
            ("react native", "React Native"), ("react", "React"), ("astro", "Astro"),
            ("postgresql", "PostgreSQL"), ("sql", "SQL"), ("linux", "Linux"),
            ("posix", "POSIX"), ("unix", "Unix"), ("multithread", "Multithreading"),
            ("mutex", "Mutex"), ("bellek", "Bellek Yönetimi"), ("memory", "Memory Management"),
            ("socket.io", "Socket.IO"), ("active directory", "Active Directory"),
            ("tcp/ip", "TCP/IP"), ("git", "Git")
        ]

        matched = []
        for kw, official in candidate_tech:
            if kw in combined:
                if official not in matched:
                    matched.append(official)

        is_intern = any(k in title_l for k in ["intern", "staj", "trainee", "genç yetenek", "graduate"])
        is_junior = "junior" in title_l
        is_senior = any(k in title_l for k in ["senior", "sr.", "lead", "principal", "yönetici", "müdür"])

        # Temel puan hesabı
        base_score = 30.0 if any(k in title_l for k in ["software", "yazılım", "developer", "mühendis"]) else 15.0
        tech_score = min(len(matched) * 12.0, 50.0)
        entry_bonus = 15.0 if is_intern else (10.0 if is_junior else 0.0)
        senior_penalty = 25.0 if is_senior else 0.0

        total_score = max(0.0, min(100.0, base_score + tech_score + entry_bonus - senior_penalty))

        if len(matched) == 0 and not is_intern:
            total_score = 0.0

        if total_score >= 65.0:
            verdict = ReviewVerdict.RECOMMENDED
        elif total_score >= 50.0:
            verdict = ReviewVerdict.BORDERLINE
        else:
            verdict = ReviewVerdict.REJECTED

        # 400 karakterlik yedek başvuru notu
        note = (
            f"42 İstanbul'un sistem mimarisi disiplini ve Nişantaşı Üniv. Yazılım Mühendisliği altyapımla, "
            f"{job.company}'ın teknoloji hedeflerine katkı sunmak istiyorum. "
            f"CoupleOS (React Native/NestJS) ve 42 Unix projelerimdeki gerçek tecrübemle hemen tam zamanlı başlayabilirim."
        )
        if len(note) > 400:
            note = note[:397] + "..."

        return ReviewResult(
            match_score=round(total_score, 1),
            verdict=verdict,
            matched_skills=matched,
            missing_skills=["Spesifik İlan Şartları"],
            reasoning=f"Deterministik analiz: {len(matched)} teknoloji eşleşti.",
            highlighted_project="42 Istanbul & CoupleOS",
            easy_apply_note=note,
            language="tr"
        )

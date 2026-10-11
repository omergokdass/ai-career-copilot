import os
import sys
import time
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Windows console encoding uyumluluğu
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from core.models import JobPosting, ReviewVerdict
from core.location_filter import is_istanbul_location
from core.domain_filter import is_relevant_domain
from core.database import ApplicationDatabase
from core.scrapers.manager import JobScraperManager
from core.ai_reviewer import AIReviewer
from core.notifier import TelegramNotifier

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class JobOrchestrator:
    """Tüm tarama, filtreleme, yapay zeka incelemesi ve bildirim adımlarını orkestre eden ana motor."""

    def __init__(self):
        self.config = self._load_search_config()
        self.db = ApplicationDatabase()
        self.scrapers = JobScraperManager(enable_linkedin=True, enable_kariyernet=True)
        self.ai = AIReviewer()
        self.notifier = TelegramNotifier()

    def _load_search_config(self) -> Dict[str, Any]:
        cfg_path = CONFIG_DIR / "search_config.yaml"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _get_shift_label(self, shift_mode: str = "auto") -> str:
        tr_tz = timezone(timedelta(hours=3))
        now_hour = datetime.now(tr_tz).hour

        if shift_mode == "1" or (shift_mode == "auto" and now_hour < 13):
            return "1. Dalga (Sabah İlanları)"
        elif shift_mode == "2" or (shift_mode == "auto" and now_hour >= 13):
            return "2. Dalga (Öğle / Kapanış İlanları)"
        return "Tam Kapsamlı Tarama"

    def run(self, max_per_query: Optional[int] = None, shift_mode: str = "auto") -> Dict[str, Any]:
        queries_cfg = self.config.get("search_queries", [])
        queries = [q["query"] if isinstance(q, dict) else str(q) for q in queries_cfg]
        if not queries:
            queries = ["Junior Software Engineer", "Software Engineering Intern", "C++ Developer", "Junior Backend Developer"]

        shift_label = self._get_shift_label(shift_mode)
        print(f"\n{'='*70}")
        print(f"🚀 AI CAREER COPILOT — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        print(f"📌 Vardiya: {shift_label} ({len(queries)} sorgu)")
        print(f"{'='*70}")

        scanned_count = 0
        matched_count = 0
        skipped_count = 0

        target_loc = self.config.get("location", {}).get("target_query", "Istanbul, Turkey")

        for query in queries:
            time.sleep(0.5)
            print(f"\n🔍 Aranıyor: '{query}' ({target_loc})...")
            found_jobs = self.scrapers.search_all(query, location=target_loc, limit_per_source=max_per_query)
            print(f"   -> Toplam {len(found_jobs)} ilan bulundu.")

            for job in found_jobs:
                # 1. Daha önce incelendi mi? (Deduplication)
                if self.db.is_job_seen(job.job_url):
                    continue

                # 2. Lokasyon Doğrulaması (SADECE İstanbul)
                is_valid_loc, loc_reason = is_istanbul_location(job.location, title=job.title)
                if not is_valid_loc:
                    print(f"   ⏩ Atlandı [Lokasyon: {loc_reason}]: {job.title} @ {job.company}")
                    job.reasoning = loc_reason
                    job.verdict = ReviewVerdict.REJECTED
                    self.db.save_job(job, status="SKIPPED")
                    skipped_count += 1
                    continue

                # 3. Pozitif Alan Doğrulaması (Yazılım / Bilişim rolü mü?)
                is_valid_role, role_reason = is_relevant_domain(job.title, description="")
                if not is_valid_role:
                    print(f"   ⏩ Atlandı [Alan Dışı: {role_reason}]: {job.title} @ {job.company}")
                    job.reasoning = role_reason
                    job.verdict = ReviewVerdict.REJECTED
                    self.db.save_job(job, status="SKIPPED")
                    skipped_count += 1
                    continue

                # 4. İlan Detayını Çek
                print(f"\n   [İnceleme] {job.title} @ {job.company} ({job.platform})")
                job = self.scrapers.fetch_details(job)

                if not job.description or len(job.description) < 40:
                    print("   ⚠️ İlan açıklaması geçici olarak çekilemedi. Sonraki taramada tekrar denenecek.")
                    continue

                scanned_count += 1

                # 5. Gemini Yapay Zeka Değerlendirmesi
                print(f"   🧠 Yapay Zeka analizi yapılıyor...")
                review_res = self.ai.review_job(job)

                job.match_score = review_res.match_score
                job.verdict = review_res.verdict
                job.matched_skills = review_res.matched_skills
                job.missing_skills = review_res.missing_skills
                job.reasoning = review_res.reasoning
                job.highlighted_project = review_res.highlighted_project
                job.easy_apply_note = review_res.easy_apply_note
                job.language = review_res.language

                print(f"   Sonuç: %{job.match_score:.1f} | Karar: {job.verdict.value} | Easy Apply: {job.is_easy_apply}")

                # 6. Baraj Kontrolü ve Bildirim
                if job.verdict == ReviewVerdict.REJECTED:
                    print(f"   ❌ Elendi: {job.reasoning}")
                    self.db.save_job(job, status="SKIPPED")
                    skipped_count += 1
                else:
                    matched_count += 1
                    self.db.save_job(job, status="NOTIFIED")
                    print(f"   ✅ Telegram'a iletiliyor ({job.verdict.value})...")
                    self.notifier.notify_job(
                        job, 
                        stats={"scanned": scanned_count, "matched": matched_count}
                    )

        # Tarama Bitiş Özeti
        if scanned_count > 0:
            self.notifier.notify_summary(
                scanned_count=scanned_count, 
                matched_count=matched_count, 
                shift_name=shift_label
            )

        summary = {
            "scanned": scanned_count,
            "matched": matched_count,
            "skipped": skipped_count,
            "timestamp": datetime.now().isoformat()
        }
        self._write_report(summary)
        return summary

    def _write_report(self, summary: Dict[str, Any]):
        today_str = datetime.now().strftime("%Y-%m-%d")
        report_path = OUTPUT_DIR / f"DAILY_REPORT_{today_str}.md"
        report_text = f"""# 📊 AI Career Copilot Günlük Tarama Raporu — {today_str}

- **İncelenen Yeni İlan:** {summary['scanned']}
- **Uygun Bulunan ve İletilen:** {summary['matched']}
- **Kriter Dışı (Atlanan):** {summary['skipped']}
- **Zaman Damgası:** {summary['timestamp']}

---
_Sistem stabil olarak 7/24 çalışmaya devam ediyor._
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"\n📄 Rapor kaydedildi: {report_path}")

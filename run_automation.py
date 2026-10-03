import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Windows console encoding uyumluluğu
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from core.db import ApplicationDB
from core.builder import ResumeBuilder, load_master_profile
from core.matcher import JobMatcher
from core.scraper import LinkedInScraper
from core.applicator import ApplicationGuardrail
from core.ai_reviewer import AIReviewer
from core.notifier import TelegramNotifier

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

def load_criteria() -> Dict[str, Any]:
    with open(BASE_DIR / "config" / "search_criteria.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class JobAutomatorOrchestrator:
    def __init__(self):
        self.profile = load_master_profile()
        self.criteria = load_criteria()
        self.db = ApplicationDB()
        self.builder = ResumeBuilder()
        self.matcher = JobMatcher()
        self.scraper = LinkedInScraper()
        self.guardrail = ApplicationGuardrail(self.profile)
        self.ai_reviewer = AIReviewer()
        self.notifier = TelegramNotifier()

    def _select_queries_for_shift(self, all_queries: List[str], shift_mode: str = "auto") -> tuple[List[str], str]:
        """Arama sorgularını 2 ana zaman dilimine böler (10:05 ve 14:05 TSI) veya tümünü seçer."""
        if shift_mode == "all" or len(all_queries) <= 6:
            return all_queries, "Tüm Kategoriler (Tam Tarama)"

        half = (len(all_queries) + 1) // 2
        shifts = {
            "1": (all_queries[0:half], "Vardiya 1 (10:05): Genç Yetenek, Staj, C/C++ & Sistem, Junior Backend"),
            "2": (all_queries[half:], "Vardiya 2 (14:05): Frontend, Web, Mobil, AI Engineer & IT Destek")
        }

        if shift_mode in shifts:
            return shifts[shift_mode]

        # "auto" ise Türkiye saatine (UTC+3) göre vardiya seç (Saat 12:00 öncesi Vardiya 1, 12:00 sonrası Vardiya 2)
        tr_tz = timezone(timedelta(hours=3))
        now_hour = datetime.now(tr_tz).hour
        if now_hour < 12:
            return shifts["1"]
        else:
            return shifts["2"]

    def run_daily_pipeline(self, max_jobs_per_query: Optional[int] = None, shift: str = "auto", time_filter_override: Optional[str] = None) -> Dict[str, Any]:
        all_queries = self.criteria.get("search_queries", ["Junior Software Engineer", "Backend Developer"])
        queries, shift_label = self._select_queries_for_shift(all_queries, shift)

        print(f"\n{'='*70}")
        print(f"🚀 İŞ BAŞVURUSU OTOMASYONU — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        print(f"📌 Dilim: {shift_label} ({len(queries)} sorgu taranacak)")
        print(f"{'='*70}")

        locations = self.criteria.get("target_locations", ["Istanbul, Turkey"])
        min_score = self.criteria.get("min_match_score", 50.0)
        time_filter = time_filter_override if time_filter_override is not None else self.criteria.get("time_filter", "r86400")
        sort_by = self.criteria.get("sort_by", "DD")
        experience_levels = self.criteria.get("experience_levels", ["1", "2", "3"])
        jobs_limit = max_jobs_per_query if max_jobs_per_query is not None else self.criteria.get("jobs_per_query", None)

        scanned_in_batch = 0
        matched_in_batch = 0
        sample_skipped_sent = 0
        new_jobs_found = 0
        processed_count = 0

        for query in queries:
            limit_str = f"Limit: {jobs_limit}" if jobs_limit else "Tüm Son 24 Saat İlanları"
            print(f"\n🔍 Aranıyor: '{query}' ({locations[0]} | Filtre: {time_filter} | {limit_str})...")
            found_jobs = self.scraper.search_jobs(
                query, 
                location=locations[0], 
                limit=jobs_limit,
                time_filter=time_filter,
                sort_by=sort_by,
                experience_levels=experience_levels
            )
            print(f"   -> {len(found_jobs)} ilan bulundu.")

            for job in found_jobs:
                job_url = job["job_url"]
                
                # Zaten işlendi mi?
                if self.db.job_exists(job_url):
                    continue

                new_jobs_found += 1
                company = job["company"]
                position = job["title"]
                print(f"\n   [İnceleme] {position} @ {company}")

                # İlan detayını çek
                job_details = self.scraper.get_job_details(job_url)
                desc = job_details.get("description", "")
                is_easy_apply = job_details.get("is_easy_apply", False)

                if not desc or len(desc) < 40:
                    print(f"   ⚠️ İlan açıklaması LinkedIn'den çekilemedi veya erişim kısıtlı. Güvenlik gereği atlanıyor.")
                    job_info = {
                        "company": company,
                        "position": position,
                        "job_url": job_url,
                        "location": job.get("location", ""),
                        "platform": "LinkedIn",
                        "match_score": 0.0,
                        "matched_skills": [],
                        "missing_skills": ["Açıklama Alınamadı"],
                        "status": "SKIPPED",
                        "pending_reason": "İlan açıklaması LinkedIn tarafından sunulmadı (erişim kısıtı / boş metin).",
                        "notes": "Eksik açıklama"
                    }
                    self.db.record_job(job_info)
                    continue

                # Uyum analizini yap
                analysis = self.matcher.analyze_job(position, desc)
                score = analysis["match_score"]
                matched_skills = analysis["matched_skills"]
                missing_skills = analysis["missing_skills"]
                is_senior = analysis.get("is_senior", False)
                is_intern_or_grad = analysis.get("is_intern_or_grad", False)

                print(f"   Uyum Puanı: %{score} (Baraj: %{min_score}) | Kıdemli: {is_senior} | Genç/Staj: {is_intern_or_grad} | Easy Apply: {is_easy_apply}")

                job_info = {
                    "company": company,
                    "position": position,
                    "job_url": job_url,
                    "location": job["location"],
                    "platform": "LinkedIn",
                    "match_score": score,
                    "matched_skills": matched_skills,
                    "missing_skills": missing_skills,
                    "is_senior": is_senior,
                    "is_intern_or_grad": is_intern_or_grad,
                    "is_easy_apply": is_easy_apply,
                }

                scanned_in_batch += 1

                if score < min_score:
                    job_info["status"] = "SKIPPED"
                    job_info["pending_reason"] = f"Düşük eşleşme skoru (%{score:.1f} < %{min_score:.1f})"
                    job_info["notes"] = analysis["fit_summary"]
                    self.db.record_job(job_info)
                    print(f"   ❌ Atlandı (Uyumsuz: %{score})")
                    if sample_skipped_sent < 1:
                        self.notifier.notify_skipped_sample(job_info, reason=job_info["pending_reason"])
                        sample_skipped_sent += 1
                    continue

                # 1. Barajı geçen ilan için Yapay Zeka Derin İncelemesi (AI Reviewer)
                print(f"   🧠 Yapay Zeka Derin İncelemesi yapılıyor...")
                ai_job_payload = {
                    "title": position,
                    "company": company,
                    "description": desc,
                    "matched_skills": matched_skills,
                    "match_score": score,
                    "missing_skills": missing_skills,
                    "is_easy_apply": is_easy_apply
                }
                ai_review = self.ai_reviewer.review_job_deeply(ai_job_payload)

                verdict = ai_review.get("verdict", "RECOMMENDED")
                lang = ai_review.get("language", "en")
                rec_pdf = ai_review.get("recommended_cv_pdf")
                job_info["language"] = lang
                job_info["recommended_cv_path"] = rec_pdf
                job_info["highlighted_project"] = ai_review.get("highlighted_project", "")

                # Eğer pozisyon açıkça Senior/Kıdemli ise, yüksek eşleşme çıksa bile BORDERLINE (Denenebilir) olarak sınıflandır
                if is_senior and verdict == "RECOMMENDED":
                    verdict = "BORDERLINE"
                    ai_review["reasoning"] = f"Kıdemli / Senior pozisyon ({position}). Yüksek tecrübe beklense de güçlü teknik altyapı ile şans denenebilir."

                if verdict == "SKIP":
                    job_info["status"] = "SKIPPED"
                    job_info["pending_reason"] = ai_review.get("reasoning", "Yapay zeka incelemesinde elendi.")
                    self.db.record_job(job_info)
                    print(f"   ❌ Yapay Zeka Tarafından Atlandı: {job_info['pending_reason']}")
                    if sample_skipped_sent < 1:
                        self.notifier.notify_skipped_sample(job_info, reason=job_info["pending_reason"])
                        sample_skipped_sent += 1
                    continue

                elif verdict == "BORDERLINE":
                    matched_in_batch += 1
                    job_info["status"] = "BORDERLINE_SUGGESTION"
                    job_info["pending_reason"] = ai_review.get("reasoning", "Sınırda eşleşme / denenebilir ilan.")
                    job_info["notes"] = f"{analysis['fit_summary']} | AI: {ai_review.get('reasoning')}"
                    self.db.record_job(job_info)
                    print(f"   💡 [DÜŞÜK İHTİMAL / DENENEBİLİR] {job_info['pending_reason']}")
                    self.notifier.notify_job_card(
                        job_info, 
                        category="BORDERLINE", 
                        stats={"scanned": scanned_in_batch, "matched": matched_in_batch}
                    )
                    processed_count += 1
                    continue

                # 2. CV Belirleme (Sabit Kural: 92 Puanlık Master ATS CV)
                master_cv = BASE_DIR / "source_resume" / "Omer_Faruk_Gokdas_CV_Master_ATS.pdf"
                if master_cv.exists():
                    job_info["tailored_cv_path"] = str(master_cv)
                    print(f"   📄 Doğrulanmış Master ATS CV seçildi: {master_cv.name}")
                else:
                    print(f"   📄 Master ATS CV bulunamadı, şablondan dinamik derleniyor...")
                    _, pdf_path = self.builder.build_cv(job_info)
                    job_info["tailored_cv_path"] = str(pdf_path)

                # 3. Özgün AI Cover Letter kaydetme (SADECE Easy Apply için)
                if is_easy_apply and ai_review.get("custom_cover_letter"):
                    clean_comp = self.builder._sanitize_filename(company)
                    clean_pos = self.builder._sanitize_filename(position)
                    cl_path = OUTPUT_DIR / "cover_letters" / f"Cover_Letter_{clean_comp}_{clean_pos}.txt"
                    with open(cl_path, "w", encoding="utf-8") as f:
                        f.write(ai_review.get("custom_cover_letter", ""))
                    job_info["cover_letter_path"] = str(cl_path)
                else:
                    job_info["cover_letter_path"] = ""
                job_info["notes"] = f"{analysis['fit_summary']} | AI: {ai_review.get('reasoning')} | Öne Çıkan: {ai_review.get('highlighted_project')}"

                # 4. Başvuru Kanalı ve Zengin Telegram Bildirimi
                matched_in_batch += 1
                if is_easy_apply:
                    job_info["status"] = "READY_TO_APPLY"
                    job_info["pending_reason"] = "Easy Apply ilanı. AI Mikro Ön Yazı (Maks. 400 Karakter) ve Master ATS CV hazırlandı."
                    print(f"   ⚡ [KOLAY BAŞVURU PAKETİ HAZIR] 400 Karakter Ön Yazı ve Master ATS CV hazır.")
                else:
                    job_info["status"] = "NEEDS_REVIEW"
                    job_info["pending_reason"] = "İşveren şirket portalına yönlendiriyor. Master ATS CV ile başvuru yapılabilir."
                    print(f"   🌐 [ŞİRKET PORTALI PAKETİ HAZIR] Şirket dış portalına yönlendirme. Master ATS CV hazır.")

                self.notifier.notify_job_card(
                    job_info, 
                    category="STRONG",
                    stats={"scanned": scanned_in_batch, "matched": matched_in_batch}
                )

                self.db.record_job(job_info)
                processed_count += 1

        # Döngü sonu özet bildirimi (Tek ve kesin rapor)
        if scanned_in_batch > 0:
            batch_summary_msg = f"""🏁 <b>TARAMA DÖNGÜSÜ TAMAMLANDI</b>
📌 <b>Dilim:</b> {shift_label}
• <b>İncelenen Yeni İlan:</b> {scanned_in_batch}
• <b>Uygun Bulunan ve Hazırlanan:</b> {matched_in_batch}
• <b>Kriter Dışı (Atlanan):</b> {max(0, scanned_in_batch - matched_in_batch)}

🚀 <i>Tüm uygun başvuru paketleri Telegram üzerinden butonlarıyla iletildi.</i>"""
            self.notifier.send_message(batch_summary_msg)

        summary = self.db.get_daily_summary()
        self._generate_markdown_report(summary)
        return summary

    def _generate_markdown_report(self, summary: Dict[str, Any]):
        today_str = summary["date"]
        report_path = OUTPUT_DIR / f"DAILY_REPORT_{today_str}.md"

        lines = [
            f"# 📊 Günlük İş Başvuru ve Tarama Raporu — {today_str}\n",
            f"- **Taranan Toplam İlan:** {summary['total_scanned']}",
            f"- **✅ Otomatik Başvurulan:** {summary['applied_auto_count']}",
            f"- **⚠️ Onay / İnceleme Bekleyen:** {summary['needs_review_count']}",
            f"- **❌ Kriter Altı (Atlanan):** {summary['skipped_count']}\n",
            "---\n",
            "## 1. Otomatik Tamamlanan Başvurular\n"
        ]

        if not summary["applied_jobs"]:
            lines.append("_Bugün otomatik tamamlanan başvuru bulunmuyor._\n")
        else:
            for job in summary["applied_jobs"]:
                lines.append(f"### 🎯 {job['position']} — {job['company']}")
                lines.append(f"- **Lokasyon:** {job['location']}")
                lines.append(f"- **Uyum Skoru:** %{job['match_score']}")
                lines.append(f"- **İlan Linki:** [{job['company']} İlanı]({job['job_url']})")
                lines.append(f"- **Kullanılan CV:** `{job['tailored_cv_path']}`")
                lines.append(f"- **Kullanılan Cover Letter:** `{job['cover_letter_path']}`")
                lines.append(f"- **Notlar:** {job['notes']}\n")

        lines.append("\n## 2. Onay / Girdi Bekleyen İlanlar\n")
        if not summary["needs_review_jobs"]:
            lines.append("_İnceleme bekleyen ilan bulunmuyor._\n")
        else:
            for job in summary["needs_review_jobs"]:
                lines.append(f"### ⚠️ {job['position']} — {job['company']}")
                lines.append(f"- **Lokasyon:** {job['location']}")
                lines.append(f"- **Uyum Skoru:** %{job['match_score']}")
                lines.append(f"- **Bekleme Nedeni:** {job['pending_reason']}")
                lines.append(f"- **İlan Linki:** [{job['company']} İlanı]({job['job_url']})")
                lines.append(f"- **Hazır CV PDF:** `{job['tailored_cv_path']}`")
                lines.append(f"- **Hazır Cover Letter:** `{job['cover_letter_path']}`\n")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"\n📄 Günlük rapor kaydedildi: {report_path}")

    def run_if_needed_today(self, force: bool = False, shift: str = "auto", time_filter_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Bilgisayar sabah 09:30'da açık olmasa bile (örn: 12:00'de açılsa bile),
        günün taraması henüz yapılmamışsa veya vardiya bazlı ise çalışmasını sağlar.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        report_path = OUTPUT_DIR / f"DAILY_REPORT_{today_str}.md"

        if report_path.exists() and not force and shift == "all":
            print(f"ℹ️ Bugünün ({today_str}) genel taraması zaten yapılmış. Mevcut rapor sunuluyor.")
            return self.db.get_daily_summary(today_str)

        return self.run_daily_pipeline(shift=shift, time_filter_override=time_filter_override)

if __name__ == "__main__":
    force_run = "--force" in sys.argv
    wide_run = "--wide" in sys.argv
    shift_arg = "auto"
    time_filter_arg = "" if wide_run else None

    for arg in sys.argv:
        if arg.startswith("--shift="):
            shift_arg = arg.split("=")[1].strip()
        elif arg == "--all":
            shift_arg = "all"
        elif arg.startswith("--time-filter="):
            time_filter_arg = arg.split("=")[1].strip()

    if "--shift" in sys.argv:
        idx = sys.argv.index("--shift")
        if idx + 1 < len(sys.argv):
            shift_arg = sys.argv[idx + 1].strip()

    automator = JobAutomatorOrchestrator()
    automator.run_if_needed_today(force=force_run, shift=shift_arg, time_filter_override=time_filter_arg)

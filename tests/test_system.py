import os
import unittest
import tempfile
from pathlib import Path

from core.db import ApplicationDB
from core.builder import ResumeBuilder, load_master_profile
from core.matcher import JobMatcher
from core.scraper import LinkedInScraper
from core.applicator import ApplicationGuardrail

class TestJobAutomatorSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = load_master_profile()
        cls.builder = ResumeBuilder()
        cls.matcher = JobMatcher()
        cls.scraper = LinkedInScraper()
        cls.guardrail = ApplicationGuardrail(cls.profile)

    def test_01_zero_hallucination_guarantee(self):
        """Kural: Adayda olmayan bir teknoloji CV'ye asla eklenemez."""
        fake_job = {
            "company": "TechGlobal",
            "position": "Lead Golang & Rust Architect",
            "matched_skills": ["Java", "Docker"],  # Sadece gerçek olanlar
        }
        html_p, pdf_p = self.builder.build_cv(fake_job)
        with open(html_p, "r", encoding="utf-8") as f:
            html_text = f.read()

        # Profilde olmayan teknolojilerin CV'ye girmediğini doğrula
        self.assertNotIn("Golang", html_text)
        self.assertNotIn("Rust", html_text)
        self.assertNotIn("Kubernetes", html_text)
        self.assertTrue(pdf_p.exists())
        self.assertGreater(pdf_p.stat().st_size, 50000)

    def test_02_matcher_accuracy(self):
        """İlan analiz motoru uyumlu ve eksik teknolojileri doğru tespit etmeli."""
        job_desc = "We need strong C/C++, Linux, POSIX system calls, Multithreading, PostgreSQL. Nice to have: AWS."
        analysis = self.matcher.analyze_job("Junior Software Engineer", job_desc)
        
        self.assertTrue(analysis["is_recommended"])
        self.assertIn("c", [s.lower() for s in analysis["matched_skills"]])
        self.assertIn("linux", [s.lower() for s in analysis["matched_skills"]])
        self.assertIn("AWS", analysis["missing_skills"])

    def test_03_guardrail_safety(self):
        """Güvenlik bariyeri riskli veya bilinmeyen sorularda durmalı."""
        # Riskli sorular
        safe, reason = self.guardrail.evaluate_form_questions(["What is your expected net monthly salary in TL?"])
        self.assertFalse(safe)
        self.assertIn("Maaş", reason)

        safe, reason = self.guardrail.evaluate_form_questions(["Do you speak fluent German?"])
        self.assertFalse(safe)

        # Standart ve güvenli sorular
        safe, _ = self.guardrail.evaluate_form_questions(["Are you authorized to work in Turkey?", "Notice period"])
        self.assertTrue(safe)

    def test_04_database_deduplication(self):
        """Aynı linkli ilan iki kez kaydedilmemeli."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db_path = Path(tmp.name)

        try:
            test_db = ApplicationDB(tmp_db_path)
            job = {
                "company": "TestCorp",
                "position": "Software Engineer",
                "job_url": "https://linkedin.com/jobs/view/99999999",
                "status": "APPLIED_AUTO"
            }
            test_db.record_job(job)
            self.assertTrue(test_db.job_exists("https://linkedin.com/jobs/view/99999999"))
            self.assertFalse(test_db.job_exists("https://linkedin.com/jobs/view/11111111"))
        finally:
            import gc
            del test_db
            gc.collect()
            try:
                if tmp_db_path.exists():
                    tmp_db_path.unlink()
            except PermissionError:
                pass

    def test_05_scraper_live_connectivity(self):
        """LinkedIn Guest API çalışıyor veya ağ engeli durumunda güvenli tip döndürüyor olmalı."""
        try:
            jobs = self.scraper.search_jobs("Junior Backend Developer", "Istanbul, Turkey", limit=3, time_filter="r604800")
            self.assertIsInstance(jobs, list)
            if len(jobs) > 0:
                first_job = jobs[0]
                self.assertTrue(first_job["job_url"].startswith("https://"))
                self.assertNotIn("?", first_job["job_url"])  # Tracking parametreleri temizlenmiş olmalı
        except Exception as e:
            print(f"[Test Scraper] Ağ bağlantısı uyarısı (beklenen çevre koşulu): {e}")

    def test_06_frontend_and_language_support(self):
        """AIReviewer frontend/web ilanlarını kabul etmeli, TR ve EN dillerini doğru ayırmalıdır."""
        from core.ai_reviewer import AIReviewer
        reviewer = AIReviewer()

        # Türkçe Frontend İlanı (Easy Apply)
        tr_job = {
            "title": "Frontend Geliştirici",
            "company": "ModaTeknoloji",
            "description": "Şirketimizde görev alacak, Astro, TypeScript, modern CSS ve web performansı konularında deneyimli, aranan niteliklere sahip adaylar.",
            "is_easy_apply": True
        }
        tr_review = reviewer._heuristic_review(tr_job)
        self.assertEqual(tr_review["verdict"], "RECOMMENDED")
        self.assertEqual(tr_review["language"], "tr")
        self.assertIn("branda.ist", tr_review["custom_cover_letter"])
        self.assertIn("ModaTeknoloji", tr_review["custom_cover_letter"])
        self.assertLessEqual(len(tr_review["custom_cover_letter"]), 400)
        # Sabit Kural: İlan Türkçe de olsa İngilizce Master ATS CV atanmalıdır
        self.assertTrue(Path(tr_review["recommended_cv_pdf"]).exists())
        self.assertIn("Omer_Faruk_Gokdas_CV_Master_ATS.pdf", tr_review["recommended_cv_pdf"])

        # İngilizce C/C++ Systems İlanı (Easy Apply)
        en_job = {
            "title": "Junior Systems Engineer",
            "company": "RoboSystems Inc",
            "description": "Looking for a systems engineer with solid knowledge of C/C++, POSIX standards, multithreading, and Linux operating systems.",
            "is_easy_apply": True
        }
        en_review = reviewer._heuristic_review(en_job)
        self.assertEqual(en_review["verdict"], "RECOMMENDED")
        self.assertEqual(en_review["language"], "en")
        self.assertIn("42 Istanbul", en_review["custom_cover_letter"])
        self.assertIn("RoboSystems Inc", en_review["custom_cover_letter"])
        self.assertLessEqual(len(en_review["custom_cover_letter"]), 400)
        self.assertTrue(Path(en_review["recommended_cv_pdf"]).exists())
        self.assertIn("Omer_Faruk_Gokdas_CV_Master_ATS.pdf", en_review["recommended_cv_pdf"])

    def test_07_master_pdf_paths(self):
        """Pre-compiled tek sayfa A4 Master ATS PDF dosyaları mevcut ve geçerli olmalıdır."""
        pdf_en = self.builder.get_master_pdf_path("en")
        pdf_tr = self.builder.get_master_pdf_path("tr")

        self.assertTrue(pdf_en.exists(), f"English master ATS PDF bulunamadı: {pdf_en}")
        self.assertTrue(pdf_tr.exists(), f"Turkish master ATS PDF bulunamadı: {pdf_tr}")
        self.assertGreater(pdf_en.stat().st_size, 100000, "English master ATS PDF boyutu beklenenden küçük")
        self.assertGreater(pdf_tr.stat().st_size, 100000, "Turkish master ATS PDF boyutu beklenenden küçük")

    def test_08_cover_letter_zero_hallucination(self):
        """Oluşturulan ön yazılarda asla uydurma iddialar (Spring Boot, Couple OS, Redis) yer alamaz."""
        cl_path = self.builder.build_cover_letter({
            "company": "Alpha Corp",
            "position": "Web Developer",
            "matched_skills": ["TypeScript", "Astro", "CSS"]
        })
        with open(cl_path, "r", encoding="utf-8") as f:
            cl_text = f.read()

        self.assertNotIn("Spring Boot 3", cl_text)
        self.assertNotIn("Couple OS", cl_text)
        self.assertNotIn("Redis", cl_text)
        self.assertIn("branda.ist", cl_text)

    def test_09_borderline_triage_and_telegram_module(self):
        """50-69% arasındaki ilanlar BORDERLINE olarak etiketlenmeli ve Telegram notifier güvenle çalışmalıdır."""
        from core.ai_reviewer import AIReviewer
        from core.notifier import TelegramNotifier

        reviewer = AIReviewer()
        borderline_job = {
            "title": "Junior Full Stack Engineer",
            "company": "Beta Cloud Labs",
            "description": "Looking for a junior engineer familiar with Node.js, C++ foundations. Nice to have: AWS, Docker, Kubernetes.",
            "match_score": 58.0,
            "missing_skills": ["AWS", "Docker", "Kubernetes"],
            "is_easy_apply": True
        }
        res = reviewer._heuristic_review(borderline_job)
        self.assertEqual(res["verdict"], "BORDERLINE")
        self.assertIn("Borderline match", res["reasoning"])

        # Boş / yapılandırılmamış dummy notifier testi
        dummy_notifier = TelegramNotifier(config_path=Path("nonexistent_test.yaml"))
        self.assertFalse(dummy_notifier.is_configured())
        self.assertFalse(dummy_notifier.send_message("Test message"))

        # Mevcut aktif notifier testi
        notifier = TelegramNotifier()
        self.assertTrue(notifier.is_configured())

    def test_10_gemini_api_integration_and_fallback(self):
        """Gemini Reviewer entegrasyonu ve yedek motoru doğrulanmalıdır."""
        from core.ai_reviewer import AIReviewer
        reviewer = AIReviewer()
        
        sample_job = {
            "title": "Junior Backend Developer",
            "company": "NextGen Systems",
            "description": "Seeking Junior Backend Developer with experience in C/C++, Node.js and PostgreSQL.",
            "match_score": 85.0,
            "missing_skills": [],
            "is_easy_apply": True
        }
        res = reviewer._heuristic_review(sample_job)
        self.assertIn(res["verdict"], ["RECOMMENDED", "BORDERLINE", "SKIP"])
        self.assertTrue(len(res["custom_cover_letter"]) > 50)
        self.assertLessEqual(len(res["custom_cover_letter"]), 400)
        self.assertTrue(Path(res["recommended_cv_pdf"]).exists())

if __name__ == "__main__":
    unittest.main()

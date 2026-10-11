import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from core.models import JobPosting, ReviewVerdict
from core.orchestrator import JobOrchestrator
from core.database import ApplicationDatabase


class TestE2EOrchestrator(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()

        self.orchestrator = JobOrchestrator()
        self.orchestrator.db = ApplicationDatabase(db_path=Path(self.temp_db.name))
        
        # Telegram Notifier'ı mockla (gerçek Telegram'a mesaj atmasın)
        self.orchestrator.notifier.send_message = MagicMock(return_value=True)

    def tearDown(self):
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_full_pipeline_flow(self):
        # 3 farklı senaryolu mock ilan
        sample_jobs = [
            # 1. Lokasyon dışı (Denizli) -> Baştan elenmeli
            JobPosting(
                platform="LinkedIn",
                title="Software Engineer",
                company="Metronet",
                location="Merkezefendi, Denizli, Türkiye",
                job_url="https://linkedin.com/jobs/view/100"
            ),
            # 2. Alan dışı meslek (Pricing Specialist) -> Baştan elenmeli
            JobPosting(
                platform="LinkedIn",
                title="Pricing Specialist",
                company="Insurance Co",
                location="Istanbul, Turkey",
                job_url="https://linkedin.com/jobs/view/200"
            ),
            # 3. Mükemmel eşleşen C++ / Backend ilanı -> Bildirilmeli
            JobPosting(
                platform="LinkedIn",
                title="Junior C++ Developer",
                company="Defence Corp",
                location="Istanbul, Turkey",
                job_url="https://linkedin.com/jobs/view/300",
                description="C++, Linux, POSIX ve bellek yönetimi bilen mühendis aranıyor. Socket.IO ve Git.",
                is_easy_apply=True
            )
        ]

        # ScraperManager'ı mockla
        self.orchestrator.scrapers.search_all = MagicMock(return_value=sample_jobs)
        self.orchestrator.scrapers.fetch_details = lambda j: j

        # Sadece 1 sorguluk test
        self.orchestrator.config["search_queries"] = [{"query": "Test", "category": "test"}]

        summary = self.orchestrator.run(max_per_query=5)

        self.assertEqual(summary["matched"], 1, "Sadece 1 uygun ilan eşleşmeli")
        self.assertEqual(summary["skipped"], 2, "2 alakasız ilan elenmeli")

        # DB kontrolleri
        self.assertTrue(self.orchestrator.db.is_job_seen("https://linkedin.com/jobs/view/100"))
        self.assertTrue(self.orchestrator.db.is_job_seen("https://linkedin.com/jobs/view/200"))
        self.assertTrue(self.orchestrator.db.is_job_seen("https://linkedin.com/jobs/view/300"))

        db_summary = self.orchestrator.db.get_summary()
        self.assertEqual(db_summary["notified_count"], 1)
        self.assertEqual(db_summary["skipped_count"], 2)


if __name__ == "__main__":
    unittest.main()

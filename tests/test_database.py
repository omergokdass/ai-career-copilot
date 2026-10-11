import unittest
import tempfile
from pathlib import Path
from core.models import JobPosting, ReviewVerdict
from core.database import ApplicationDatabase


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db = ApplicationDatabase(db_path=Path(self.temp_file.name))

    def tearDown(self):
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_deduplication(self):
        url = "https://www.linkedin.com/jobs/view/12345678"
        self.assertFalse(self.db.is_job_seen(url))

        job = JobPosting(
            platform="LinkedIn",
            title="Junior Software Engineer",
            company="Tech Corp",
            location="Istanbul, Turkey",
            job_url=url,
            match_score=75.0,
            verdict=ReviewVerdict.RECOMMENDED
        )
        self.db.save_job(job, status="NOTIFIED")

        # Şimdi kayıtlı olmalı
        self.assertTrue(self.db.is_job_seen(url))
        # Parametreli url de yakalanmalı
        self.assertTrue(self.db.is_job_seen(f"{url}?refId=xyz"))

    def test_summary_counts(self):
        job1 = JobPosting(
            platform="LinkedIn",
            title="Dev 1",
            company="Comp A",
            location="Istanbul",
            job_url="https://linkedin.com/jobs/view/1",
            match_score=80.0,
            verdict=ReviewVerdict.RECOMMENDED
        )
        job2 = JobPosting(
            platform="Kariyer.net",
            title="Dev 2",
            company="Comp B",
            location="Istanbul",
            job_url="https://kariyer.net/is-ilani/2",
            match_score=40.0,
            verdict=ReviewVerdict.REJECTED
        )
        self.db.save_job(job1, status="NOTIFIED")
        self.db.save_job(job2, status="SKIPPED")

        summary = self.db.get_summary()
        self.assertEqual(summary["total_recorded"], 2)
        self.assertEqual(summary["notified_count"], 1)
        self.assertEqual(summary["recommended_count"], 1)
        self.assertEqual(summary["skipped_count"], 1)


if __name__ == "__main__":
    unittest.main()

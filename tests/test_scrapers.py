import unittest
from unittest.mock import MagicMock
from core.models import JobPosting
from core.scrapers.linkedin_scraper import LinkedInScraper
from core.scrapers.kariyernet_scraper import KariyerNetScraper
from core.scrapers.manager import JobScraperManager


class TestScrapers(unittest.TestCase):

    def test_linkedin_card_parsing(self):
        scraper = LinkedInScraper()
        mock_html = """
        <div class="base-card">
            <h3 class="base-search-card__title">Junior C++ Developer</h3>
            <h4 class="base-search-card__subtitle">Roketsan</h4>
            <span class="job-search-card__location">Istanbul, Turkey</span>
            <a href="https://tr.linkedin.com/jobs/view/1234567890?refId=xyz"></a>
        </div>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_html
        scraper.session.get = MagicMock(return_value=mock_resp)

        jobs = scraper.search_jobs("C++", "Istanbul, Turkey", limit=1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Junior C++ Developer")
        self.assertEqual(jobs[0].company, "Roketsan")
        self.assertEqual(jobs[0].job_url, "https://tr.linkedin.com/jobs/view/1234567890")

    def test_kariyernet_card_parsing(self):
        scraper = KariyerNetScraper()
        mock_html = """
        <a href="/is-ilani/yazilim-stajyeri-34567">
            Yazılım Stajyeri   Aselsan
        </a>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_html
        scraper.session.get = MagicMock(return_value=mock_resp)

        jobs = scraper.search_jobs("yazılım stajyeri", limit=1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Yazılım Stajyeri")
        self.assertEqual(jobs[0].company, "Aselsan")
        self.assertEqual(jobs[0].job_url, "https://www.kariyer.net/is-ilani/yazilim-stajyeri-34567")

    def test_manager_deduplicates_and_combines(self):
        manager = JobScraperManager(enable_linkedin=True, enable_kariyernet=True)
        # Mock alt scraper'lar
        manager.linkedin.search_jobs = MagicMock(return_value=[
            JobPosting(platform="LinkedIn", title="Dev 1", company="A", location="Istanbul", job_url="https://x.com/1")
        ])
        manager.kariyernet.search_jobs = MagicMock(return_value=[
            JobPosting(platform="Kariyer.net", title="Dev 2", company="B", location="Istanbul", job_url="https://x.com/2"),
            JobPosting(platform="Kariyer.net", title="Dev 1 duplicate", company="A", location="Istanbul", job_url="https://x.com/1")
        ])

        combined = manager.search_all("Software")
        self.assertEqual(len(combined), 2, "Aynı URL'ye sahip ilanlar tekilleştirilmeli")


if __name__ == "__main__":
    unittest.main()

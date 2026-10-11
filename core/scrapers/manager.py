from typing import List, Optional
from core.models import JobPosting
from core.scrapers.linkedin_scraper import LinkedInScraper
from core.scrapers.kariyernet_scraper import KariyerNetScraper


class JobScraperManager:
    """LinkedIn ve Kariyer.net üzerinde paralel/birleşik tarama ve detay çekme yöneticisi."""

    def __init__(self, enable_linkedin: bool = True, enable_kariyernet: bool = True):
        self.linkedin = LinkedInScraper() if enable_linkedin else None
        self.kariyernet = KariyerNetScraper() if enable_kariyernet else None

    def search_all(self, keyword: str, location: str = "Istanbul, Turkey", limit_per_source: Optional[int] = None) -> List[JobPosting]:
        all_jobs: List[JobPosting] = []

        # 1. LinkedIn Araması
        if self.linkedin:
            try:
                li_jobs = self.linkedin.search_jobs(keyword, location=location, limit=limit_per_source)
                for j in li_jobs:
                    if not any(x.job_url == j.job_url for x in all_jobs):
                        all_jobs.append(j)
            except Exception as e:
                print(f"[Manager] LinkedIn arama hatası: {e}")

        # 2. Kariyer.net Araması
        if self.kariyernet:
            try:
                kn_jobs = self.kariyernet.search_jobs(keyword, location=location, limit=limit_per_source)
                for j in kn_jobs:
                    if not any(x.job_url == j.job_url for x in all_jobs):
                        all_jobs.append(j)
            except Exception as e:
                print(f"[Manager] Kariyer.net arama hatası: {e}")

        return all_jobs

    def fetch_details(self, job: JobPosting) -> JobPosting:
        if job.platform == "Kariyer.net" and self.kariyernet:
            return self.kariyernet.fetch_job_details(job)
        elif self.linkedin:
            return self.linkedin.fetch_job_details(job)
        return job

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from core.models import JobPosting


class BaseScraper(ABC):
    """Tüm platform scraper'ları için standart arayüz."""
    
    @abstractmethod
    def search_jobs(self, keyword: str, location: str, limit: Optional[int] = None) -> List[JobPosting]:
        """Belirtilen anahtar kelime ve konum için ilan listesini döndürür."""
        pass

    @abstractmethod
    def fetch_job_details(self, job: JobPosting) -> JobPosting:
        """İlanın detay açıklamasını ve başvuru türünü (Easy Apply vs.) günceller."""
        pass

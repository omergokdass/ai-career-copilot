import re
import time
import random
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

class LinkedInScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,tr;q=0.8"
        }

    def search_jobs(
        self, 
        keyword: str, 
        location: str = "Istanbul, Turkey", 
        limit: int = 10,
        time_filter: Optional[str] = "r86400",  # r3600 (1 saat), r86400 (24 saat), r604800 (1 hafta)
        sort_by: Optional[str] = "DD",         # DD: Date Descending (en güncel)
        experience_levels: Optional[List[str]] = None  # ['1', '2', '3'] -> Internship, Entry, Associate
    ) -> List[Dict[str, Any]]:
        """
        LinkedIn Guest API üzerinden parametreli, filtrelenmiş ve sayfalama destekli güncel iş araması yapar.
        """
        jobs = []
        start = 0
        batch_size = 25

        while len(jobs) < limit:
            params = {
                "keywords": keyword,
                "location": location,
                "start": start
            }

            if time_filter:
                params["f_TPR"] = time_filter
            if sort_by:
                params["sortBy"] = sort_by
            if experience_levels:
                params["f_E"] = ",".join(experience_levels)

            query_string = urllib.parse.urlencode(params)
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{query_string}"

            req = urllib.request.Request(url, headers=self.headers)
            new_in_batch = 0

            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")

                # İlan kartlarını ayıkla
                cards = html.split('<div class="base-card')
                if len(cards) <= 1:
                    # Daha fazla ilan kalmadı veya sayfa boş
                    break

                for card in cards[1:]:
                    title_match = re.search(r'class="base-search-card__title">\s*([^<]+?)\s*</h3>', card)
                    company_match = re.search(r'class="base-search-card__subtitle">[\s\S]*?<a[^>]*>\s*([^<]+?)\s*</a>', card)
                    if not company_match:
                        company_match = re.search(r'class="base-search-card__subtitle">\s*([^<]+?)\s*</h4>', card)
                    loc_match = re.search(r'class="job-search-card__location">\s*([^<]+?)\s*</span>', card)
                    link_match = re.search(r'href="(https://[a-z]{2,3}\.linkedin\.com/jobs/view/[^"?\s]+)', card)

                    if title_match and link_match:
                        title = title_match.group(1).strip()
                        company = company_match.group(1).strip() if company_match else "Unknown"
                        job_loc = loc_match.group(1).strip() if loc_match else location
                        raw_link = link_match.group(1).strip()
                        clean_link = raw_link.split("?")[0]

                        # Çift kayıt önleme
                        if not any(j["job_url"] == clean_link for j in jobs):
                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": job_loc,
                                "job_url": clean_link,
                                "platform": "LinkedIn"
                            })
                            new_in_batch += 1

                    if len(jobs) >= limit:
                        break

                if new_in_batch == 0:
                    # Bu sayfadan yeni ilan gelmedi, döngüyü bitir
                    break

                start += batch_size
                time.sleep(random.uniform(0.3, 0.7))

            except Exception as e:
                print(f"[Scraper] Uyarı ({keyword} @ start={start}): {e}")
                break

        return jobs

    def get_job_description(self, job_url: str) -> str:
        """İlan detay sayfasından gereksinimleri ve tam açıklamayı çeker."""
        job_id_match = re.search(r'-(\d+)$', job_url.rstrip("/"))
        if not job_id_match:
            job_id_match = re.search(r'/view/(\d+)', job_url)

        if job_id_match:
            job_id = job_id_match.group(1)
            detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
            try:
                req = urllib.request.Request(detail_url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                
                clean_text = re.sub(r'<[^>]+>', ' ', html)
                clean_text = ' '.join(clean_text.split())
                return clean_text
            except Exception:
                pass

        return ""

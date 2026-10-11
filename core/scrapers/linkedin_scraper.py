import re
import html
import time
import random
from typing import List, Optional
import requests

from core.models import JobPosting
from core.scrapers.base import BaseScraper


class LinkedInScraper(BaseScraper):
    """LinkedIn Guest API üzerinden üyelik/giriş gerektirmeden çalışan kararlı iş arama motoru."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,tr;q=0.8"
        })

    def search_jobs(self, keyword: str, location: str = "Istanbul, Turkey", limit: Optional[int] = None) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        start = 0
        max_pages = 10
        page = 0

        while page < max_pages:
            if limit and len(jobs) >= limit:
                break

            page += 1
            params = {
                "keywords": keyword,
                "location": location,
                "f_TPR": "r86400",  # Son 24 saatteki ilanlar
                "sortBy": "DD",     # En yeni tarihliler üstte
                "start": start
            }

            url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            try:
                resp = self.session.get(url, params=params, timeout=12)
                if resp.status_code != 200:
                    break

                html_content = resp.text
                cards = html_content.split('<div class="base-card')
                if len(cards) <= 1:
                    break

                new_on_page = 0
                for card in cards[1:]:
                    title_m = re.search(r'class="base-search-card__title">\s*([^<]+?)\s*</h3>', card)
                    comp_m = re.search(r'class="base-search-card__subtitle">[\s\S]*?<a[^>]*>\s*([^<]+?)\s*</a>', card)
                    if not comp_m:
                        comp_m = re.search(r'class="base-search-card__subtitle">\s*([^<]+?)\s*</h4>', card)
                    loc_m = re.search(r'class="job-search-card__location">\s*([^<]+?)\s*</span>', card)
                    link_m = re.search(r'href="(https://[a-z]{2,3}\.linkedin\.com/jobs/view/[^"?\s]+)', card)

                    if title_m and link_m:
                        raw_title = title_m.group(1).strip()
                        raw_comp = comp_m.group(1).strip() if comp_m else "Bilinmeyen Şirket"
                        raw_loc = loc_m.group(1).strip() if loc_m else location
                        raw_url = link_m.group(1).strip().split("?")[0]

                        title = html.unescape(raw_title)
                        company = html.unescape(raw_comp)
                        job_loc = html.unescape(raw_loc)

                        if not any(j.job_url == raw_url for j in jobs):
                            jobs.append(JobPosting(
                                platform="LinkedIn",
                                title=title,
                                company=company,
                                location=job_loc,
                                job_url=raw_url
                            ))
                            new_on_page += 1

                    if limit and len(jobs) >= limit:
                        break

                if new_on_page == 0:
                    break

                start += (len(cards) - 1)
                time.sleep(random.uniform(0.3, 0.6))

            except Exception as e:
                print(f"[LinkedInScraper] Hata ({keyword} @ sayfa={page}): {e}")
                break

        return jobs

    def fetch_job_details(self, job: JobPosting) -> JobPosting:
        """İlan detay sayfasından tam metni ve Easy Apply durumunu çeker."""
        job_id_match = re.search(r'-(\d+)$', job.job_url.rstrip("/"))
        if not job_id_match:
            job_id_match = re.search(r'/view/(\d+)', job.job_url)

        if not job_id_match:
            return job

        job_id = job_id_match.group(1)
        detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

        try:
            resp = self.session.get(detail_url, timeout=12)
            if resp.status_code == 200:
                html_resp = resp.text

                # Easy Apply (Onsite) vs. Şirket Portalı (Offsite)
                is_onsite = bool(re.search(r'apply-link-simple_onsite|apply-link-onsite|guest-to-member-job-apply=enabled|easy[-_]?apply', html_resp, re.I))
                is_offsite = bool(re.search(r'offsite-apply-icon-svg|apply-link-offsite', html_resp, re.I))
                job.is_easy_apply = is_onsite and not is_offsite

                # Açıklama metnini ayıkla
                markup_m = re.search(r'class="[^"]*show-more-less-html__markup[^"]*">([\s\S]*?)</div>', html_resp)
                if not markup_m:
                    markup_m = re.search(r'<section[^>]*class="[^"]*description[^"]*"[^>]*>([\s\S]*?)</section>', html_resp)
                
                raw_desc = markup_m.group(1) if markup_m else html_resp
                
                # HTML temizliği
                clean = re.sub(r'<(?:br|/p|/li|/div|/h[1-6])[^>]*>', '\n', raw_desc, flags=re.I)
                clean = re.sub(r'<[^>]+>', ' ', clean)
                clean = '\n'.join(' '.join(line.split()) for line in clean.split('\n') if line.strip())
                job.description = html.unescape(clean)

        except Exception as e:
            print(f"[LinkedInScraper] Detay çekme uyarısı ({job.title}): {e}")

        return job

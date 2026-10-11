import re
import html
import urllib.parse
from typing import List, Optional
import requests

from core.models import JobPosting
from core.scrapers.base import BaseScraper


class KariyerNetScraper(BaseScraper):
    """Kariyer.net üzerindeki güncel İstanbul yazılım ve staj ilanlarını tarayan motor."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.kariyer.net/is-ilanlari"
        })

    def search_jobs(self, keyword: str, location: str = "Istanbul, Turkey", limit: Optional[int] = None) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        
        # Türkçe karşılık haritası
        tr_map = {
            "Software Engineering Intern": "yazılım stajyeri",
            "Genç Yetenek Yazılım": "genç yetenek yazılım",
            "Junior Software Engineer": "junior yazılım",
            "Junior C++ Developer": "c++ yazılım",
            "C++ Developer": "c++ geliştirici",
            "Junior Backend Developer": "backend geliştirici",
            "Junior Frontend Developer": "frontend geliştirici",
            "TypeScript Developer": "typescript",
            "React Native Developer": "react native",
            "Junior AI Engineer": "yapay zeka",
            "IT Support Specialist": "it destek"
        }
        search_kw = tr_map.get(keyword, keyword)
        encoded_kw = urllib.parse.quote(search_kw)
        url = f"https://www.kariyer.net/is-ilanlari/istanbul?kw={encoded_kw}"

        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return jobs

            html_resp = resp.text
            job_links = re.findall(r'href="(/is-ilani/[^"]+)"[^>]*>([\s\S]*?)</a>', html_resp)

            for href, raw_content in job_links:
                clean_text = re.sub(r'<[^>]+>', ' ', raw_content)
                parts = [p.strip() for p in re.split(r'\s{2,}|\n', clean_text) if p.strip()]
                title = html.unescape(parts[0] if parts else "Yazılım Pozisyonu")
                company = html.unescape(parts[1] if len(parts) > 1 else "Kariyer.net İşvereni")

                full_url = f"https://www.kariyer.net{href.split('?')[0]}"
                if not any(j.job_url == full_url for j in jobs):
                    jobs.append(JobPosting(
                        platform="Kariyer.net",
                        title=title,
                        company=company,
                        location="Istanbul, Türkiye",
                        job_url=full_url,
                        is_easy_apply=False
                    ))

                if limit and len(jobs) >= limit:
                    break

        except Exception as e:
            print(f"[KariyerNetScraper] Arama hatası ({keyword}): {e}")

        return jobs

    def fetch_job_details(self, job: JobPosting) -> JobPosting:
        try:
            resp = self.session.get(job.job_url, timeout=15)
            if resp.status_code == 200:
                html_resp = resp.text
                desc_m = re.search(r'class="job-detail"[^>]*>([\s\S]*?)</section>', html_resp) or \
                         re.search(r'class="job-detail-content"[^>]*>([\s\S]*?)</div>', html_resp) or \
                         re.search(r'itemprop="description"[^>]*>([\s\S]*?)</div>', html_resp)
                
                raw_desc = desc_m.group(1) if desc_m else html_resp
                clean = re.sub(r'<(?:br|/p|/li|/div|/h[1-6])[^>]*>', '\n', raw_desc, flags=re.I)
                clean = re.sub(r'<[^>]+>', ' ', clean)
                clean = '\n'.join(' '.join(line.split()) for line in clean.split('\n') if line.strip())
                job.description = html.unescape(clean)

        except Exception as e:
            print(f"[KariyerNetScraper] Detay çekme uyarısı ({job.title}): {e}")

        return job

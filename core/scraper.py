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
        limit: Optional[int] = None,
        time_filter: Optional[str] = "r86400",  # r3600 (1 saat), r86400 (24 saat), r604800 (1 hafta)
        sort_by: Optional[str] = "DD",         # DD: Date Descending (en güncel)
        experience_levels: Optional[List[str]] = None  # ['1', '2', '3'] -> Internship, Entry, Associate
    ) -> List[Dict[str, Any]]:
        """
        LinkedIn Guest API üzerinden parametreli, filtrelenmiş ve sayfalama destekli güncel iş araması yapar.
        Sayfalama hatası düzeltilmiştir (dönen kart sayısına göre offset artırılarak hiçbir ilan atlanmaz).
        """
        jobs = []
        start = 0
        max_pages = 10
        page = 0

        while page < max_pages:
            if limit is not None and limit > 0 and len(jobs) >= limit:
                break

            page += 1
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

                    if limit is not None and limit > 0 and len(jobs) >= limit:
                        break

                if new_in_batch == 0:
                    break

                # Dinamik sayfalama düzeltmesi: Dönen kart sayısı kadar ilerle
                card_count = len(cards) - 1
                start += card_count
                time.sleep(random.uniform(0.4, 0.8))

            except Exception as e:
                print(f"[LinkedInScraper] Uyarı ({keyword} @ start={start}): {e}")
                break

        return jobs

    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """İlan detay sayfasından gereksinimleri, açıklamayı ve Easy Apply durumunu tam olarak çeker."""
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

                # Easy Apply (Onsite) vs. Şirket Portalı (Offsite) Tespiti
                is_onsite = bool(re.search(r'apply-link-simple_onsite|apply-link-onsite|guest-to-member-job-apply=enabled|easy[-_]?apply', html, re.I))
                is_offsite = bool(re.search(r'offsite-apply-icon-svg|apply-link-offsite', html, re.I))
                is_easy_apply = is_onsite and not is_offsite

                # Açıklama gövdesini ayıkla
                markup_match = re.search(r'class="[^"]*show-more-less-html__markup[^"]*">([\s\S]*?)</div>', html)
                if markup_match:
                    raw_desc = markup_match.group(1)
                else:
                    section_match = re.search(r'<section[^>]*class="[^"]*description[^"]*"[^>]*>([\s\S]*?)</section>', html)
                    raw_desc = section_match.group(1) if section_match else html

                clean_desc = re.sub(r'<(?:br|/p|/li|/div|/h[1-6])[^>]*>', '\n', raw_desc, flags=re.I)
                clean_desc = re.sub(r'<[^>]+>', ' ', clean_desc)
                clean_desc = '\n'.join(' '.join(line.split()) for line in clean_desc.split('\n') if line.strip())

                return {
                    "description": clean_desc,
                    "is_easy_apply": is_easy_apply
                }
            except Exception:
                pass

        return {"description": "", "is_easy_apply": False}

    def get_job_description(self, job_url: str) -> str:
        return self.get_job_details(job_url)["description"]


class KariyerNetScraper:
    """Kariyer.net üzerindeki güncel Türkçe yazılım ve staj ilanlarını tarayan scraper."""
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.kariyer.net/is-ilanlari"
        }

    def search_jobs(self, keyword: str, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
        jobs = []
        encoded_kw = urllib.parse.quote(keyword)
        url = f"https://www.kariyer.net/is-ilanlari?kw={encoded_kw}"

        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # İlan linklerini ve başlıklarını yakala
            job_links = re.findall(r'href="(/is-ilani/[^"]+)"[^>]*>([\s\S]*?)</a>', html)
            for href, raw_content in job_links:
                clean_text = re.sub(r'<[^>]+>', ' ', raw_content)
                clean_text = ' '.join(clean_text.split())

                # Pozisyon adını ayrıştır
                parts = clean_text.split("   ")
                title = parts[0].strip() if parts else clean_text
                company = parts[1].strip() if len(parts) > 1 else "Kariyer.net Şirketi"

                full_url = f"https://www.kariyer.net{href.split('?')[0]}"
                if not any(j["job_url"] == full_url for j in jobs):
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": "Türkiye",
                        "job_url": full_url,
                        "platform": "Kariyer.net"
                    })

                if limit and len(jobs) >= limit:
                    break

        except Exception as e:
            print(f"[KariyerNetScraper] Hata ({keyword}): {e}")

        return jobs

    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        req = urllib.request.Request(job_url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Açıklama metnini ayıkla
            desc_match = re.search(r'class="job-detail"[^>]*>([\s\S]*?)</section>', html) or \
                         re.search(r'class="job-detail-content"[^>]*>([\s\S]*?)</div>', html) or \
                         re.search(r'itemprop="description"[^>]*>([\s\S]*?)</div>', html)
            if desc_match:
                raw_desc = desc_match.group(1)
            else:
                raw_desc = html

            clean_desc = re.sub(r'<(?:br|/p|/li|/div|/h[1-6])[^>]*>', '\n', raw_desc, flags=re.I)
            clean_desc = re.sub(r'<[^>]+>', ' ', clean_desc)
            clean_desc = '\n'.join(' '.join(line.split()) for line in clean_desc.split('\n') if line.strip())

            return {
                "description": clean_desc,
                "is_easy_apply": False  # Kariyer.net dış başvuru / portal yönlendirmesi
            }
        except Exception:
            pass

        return {"description": "", "is_easy_apply": False}


class MultiPlatformScraper:
    """LinkedIn ve Kariyer.net üzerinde birleşik arama ve detay çekme motoru."""
    def __init__(self):
        self.linkedin = LinkedInScraper()
        self.kariyer = KariyerNetScraper()

    def search_jobs(
        self, 
        keyword: str, 
        location: str = "Istanbul, Turkey", 
        limit: Optional[int] = None,
        time_filter: Optional[str] = "r86400",
        sort_by: Optional[str] = "DD",
        experience_levels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        # 1. LinkedIn Araması
        all_jobs = self.linkedin.search_jobs(
            keyword=keyword,
            location=location,
            limit=limit,
            time_filter=time_filter,
            sort_by=sort_by,
            experience_levels=experience_levels
        )

        # 2. Kariyer.net Araması (Türkçe anahtar kelimeler ve genel roller için ekle)
        tr_keywords_map = {
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
            "AI Developer": "yapay zeka mühendisi",
            "IT Support Specialist": "it destek uzmanı"
        }
        kariyer_kw = tr_keywords_map.get(keyword, keyword)
        kariyer_jobs = self.kariyer.search_jobs(kariyer_kw, limit=5)
        for kj in kariyer_jobs:
            if not any(j["job_url"] == kj["job_url"] for j in all_jobs):
                all_jobs.append(kj)

        return all_jobs

    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        if "kariyer.net" in job_url:
            return self.kariyer.get_job_details(job_url)
        return self.linkedin.get_job_details(job_url)

    def get_job_description(self, job_url: str) -> str:
        return self.get_job_details(job_url)["description"]

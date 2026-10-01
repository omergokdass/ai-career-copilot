import os
import subprocess
import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any, Tuple, Optional

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
TAILORED_CVS_DIR = OUTPUT_DIR / "tailored_cvs"
COVER_LETTERS_DIR = OUTPUT_DIR / "cover_letters"

# Ensure output directories exist
TAILORED_CVS_DIR.mkdir(parents=True, exist_ok=True)
COVER_LETTERS_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium"
]

def get_browser_path() -> str:
    import shutil
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    for cmd in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
        found = shutil.which(cmd)
        if found:
            return found
    raise FileNotFoundError("Google Chrome veya Chromium bulunamadı.")

def load_master_profile() -> Dict[str, Any]:
    profile_path = CONFIG_DIR / "master_profile.yaml"
    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class ResumeBuilder:
    def __init__(self):
        self.profile = load_master_profile()
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False
        )

    def _sanitize_filename(self, text: str) -> str:
        keep = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in text)
        return "_".join(keep.split())

    def _select_role_title(self, job_title: str, matched_skills: list) -> str:
        title_lower = job_title.lower()
        skills_lower = [s.lower() for s in matched_skills]

        if any(k in title_lower for k in ["frontend", "front-end", "web developer", "web geliştirici", "astro", "typescript", "javascript", "ui developer"]):
            return self.profile["role_titles"].get("frontend", self.profile["personal"]["default_title"])
        elif any(k in title_lower for k in ["c++", "c ", "embedded", "systems", "linux", "kernel", "gömülü"]):
            return self.profile["role_titles"].get("systems", self.profile["personal"]["default_title"])
        elif any(k in title_lower for k in ["junior", "intern", "staj", "graduate", "talent", "yeni mezun"]):
            return self.profile["role_titles"].get("junior", self.profile["personal"]["default_title"])
        elif "backend" in title_lower or any("node" in s for s in skills_lower):
            return self.profile["role_titles"].get("backend", self.profile["personal"]["default_title"])
        return self.profile["personal"]["default_title"]

    def _prioritize_projects(self, matched_skills: list) -> list:
        """İlanın gereksinimlerine göre en ilgili projeleri öne alır (içeriği asla değiştirmeden)."""
        skills_set = {s.lower() for s in matched_skills}
        projects = list(self.profile["projects"])

        def project_score(proj):
            score = 0
            for tag in proj.get("tags", []):
                if tag.lower() in skills_set or any(tag.lower() in s for s in skills_set):
                    score += 2
            return score

        # Skoru yüksek olan projeleri üste sırala
        projects.sort(key=project_score, reverse=True)
        return projects

    def _prioritize_skills(self, matched_skills: list) -> dict:
        """Yetenek listesinde ilanda geçen maddeleri kendi kategorisi içinde öne taşır."""
        skills_set = {s.lower() for s in matched_skills}
        ordered_skills = {}

        for cat_key, cat_data in self.profile["skills"].items():
            category_name = cat_data["category_name"]
            items = list(cat_data["items"])

            def item_priority(item):
                item_lower = item.lower()
                is_matched = any(item_lower in s or s in item_lower for s in skills_set)
                return 0 if is_matched else 1

            items.sort(key=item_priority)
            ordered_skills[cat_key] = {
                "category_name": category_name,
                "items": items
            }

        return ordered_skills

    def build_cv(self, job_info: Dict[str, Any]) -> Tuple[Path, Path]:
        """
        İlana özel ATS uyumlu HTML ve PDF CV oluşturur.
        Returns: (html_path, pdf_path)
        """
        company = self._sanitize_filename(job_info.get("company", "Company"))
        position = self._sanitize_filename(job_info.get("position", "Software_Engineer"))
        matched_skills = job_info.get("matched_skills", [])

        target_title = self._select_role_title(job_info.get("position", ""), matched_skills)
        prioritized_projects = self._prioritize_projects(matched_skills)
        prioritized_skills = self._prioritize_skills(matched_skills)

        template = self.jinja_env.get_template("cv_ats_template.html")
        html_content = template.render(
            profile=self.profile,
            target_title=target_title,
            skills=prioritized_skills,
            experience=self.profile["experience"],
            projects=prioritized_projects
        )

        base_name = f"Omer_Faruk_Gokdas_CV_{company}_{position}"
        html_path = TAILORED_CVS_DIR / f"{base_name}.html"
        pdf_path = TAILORED_CVS_DIR / f"{base_name}.pdf"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Chrome Headless ile PDF çıktısı al
        browser_exe = get_browser_path()
        file_url = html_path.as_uri()
        cmd = [
            browser_exe,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            file_url
        ]

        result = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
        if not pdf_path.exists():
            # Eski headless argümanını dene
            cmd[1] = "--headless"
            subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")

        if not pdf_path.exists():
            raise RuntimeError(f"PDF oluşturulamadı: {result.stderr}")

        return html_path, pdf_path

    def build_cover_letter(self, job_info: Dict[str, Any]) -> Path:
        """
        İlana ve şirkete özel, dürüst ve özgün Cover Letter üretir.
        """
        company = job_info.get("company", "the hiring company")
        position = job_info.get("position", "Software Engineer")
        matched_skills = job_info.get("matched_skills", [])

        # Ana teknoloji cümlesini ilana göre seç (Tamamen gerçek ve doğrulanmış yetenek havuzu)
        skills_lower = [s.lower() for s in matched_skills]
        if any(k in skills_lower for k in ["astro", "typescript", "frontend", "web", "html", "css", "purgecss", "sharp"]):
            primary_stack = "Astro, TypeScript, Static Site Generation (SSG), and modern responsive web layouts"
            secondary_highlight = "Architected and published branda.ist (80+ page commercial platform) using Astro, TypeScript, Sharp, and PurgeCSS with sub-1.5s load times."
        elif any(k in skills_lower for k in ["c++", "c", "systems", "posix", "linux", "kernel", "multithreading"]):
            primary_stack = "C/C++, POSIX Unix standards, multithreading, and memory-safe systems programming"
            secondary_highlight = "Engineered Minishell (POSIX Unix shell) with custom process control, pipes, and Valgrind-verified leak-free memory management at 42 Istanbul."
        elif any(k in skills_lower for k in ["node", "express", "socket", "backend", "postgresql", "sql"]):
            primary_stack = "Node.js, Express, Socket.IO, and PostgreSQL relational database design"
            secondary_highlight = "Designed NishChat real-time campus messaging platform with low-latency WebSocket channels and relational database modeling."
        elif any(k in skills_lower for k in ["bash", "active directory", "infrastructure", "networking", "tcp/ip"]):
            primary_stack = "Active Directory, TCP/IP networking, Linux CLI, and Bash automation"
            secondary_highlight = "Administered municipal network infrastructure and developed Bash automation scripts for routine diagnostics during IT internship at Besiktas Municipality."
        else:
            primary_stack = "C/C++, POSIX Unix standards, TypeScript, and software architecture principles"
            secondary_highlight = "Combining a Bachelor's in Software Engineering from Nisantasi University with the intensive systems programming curriculum at 42 Istanbul."

        company_appeal = f"the impactful products your team is building and the high engineering standards at {company}"

        template = self.jinja_env.get_template("cover_letter_template.txt")
        cover_content = template.render(
            company_name=company,
            job_title=position,
            hiring_manager=job_info.get("hiring_manager", "Hiring Team"),
            candidate_name=self.profile["personal"]["full_name"].title(),
            candidate_phone=self.profile["personal"]["phone"],
            candidate_email=self.profile["personal"]["email"],
            candidate_linkedin=self.profile["personal"]["linkedin"],
            candidate_github=self.profile["personal"]["github"],
            primary_stack_bullet=primary_stack,
            secondary_highlight_bullet=secondary_highlight,
            company_appeal_reason=company_appeal
        )

        clean_company = self._sanitize_filename(company)
        clean_position = self._sanitize_filename(position)
        cl_path = COVER_LETTERS_DIR / f"Cover_Letter_{clean_company}_{clean_position}.txt"

        with open(cl_path, "w", encoding="utf-8") as f:
            f.write(cover_content)

        return cl_path

    def get_master_pdf_path(self, language: str = "en") -> Path:
        """Doğrulanmış ve tek sayfa A4 formatındaki hazır Master ATS PDF yolunu döndürür."""
        if language.lower() in ("tr", "turkish", "türkçe"):
            rel_path = self.profile["personal"].get("master_cv_tr_pdf", "source_resume/Omer_Faruk_Gokdas_CV_Master_ATS_TR.pdf")
        else:
            rel_path = self.profile["personal"].get("master_cv_en_pdf", "source_resume/Omer_Faruk_Gokdas_CV_Master_ATS.pdf")
        full_path = BASE_DIR / rel_path
        if full_path.exists():
            return full_path
        desktop_pdf = Path(r"C:\Users\faruk\OneDrive\Masaüstü\resume\pdf") / (
            "Omer_Faruk_Gokdas_CV_Master_ATS_TR.pdf" if language.lower() in ("tr", "turkish", "türkçe") else "Omer_Faruk_Gokdas_CV_Master_ATS.pdf"
        )
        if desktop_pdf.exists():
            return desktop_pdf
        return full_path

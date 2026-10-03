import re
import yaml
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"

def load_configs():
    with open(CONFIG_DIR / "master_profile.yaml", "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    with open(CONFIG_DIR / "search_criteria.yaml", "r", encoding="utf-8") as f:
        criteria = yaml.safe_load(f)
    return profile, criteria

class JobMatcher:
    def __init__(self):
        self.profile, self.criteria = load_configs()
        self.candidate_skills = self._extract_all_candidate_skills()

    def _extract_all_candidate_skills(self) -> Dict[str, str]:
        """Adayın tüm gerçek yeteneklerini küçük harf -> resmi ad haritası olarak çıkarır."""
        GENERIC_STOP_WORDS = {
            "support", "systems", "production", "ai", "operations", "troubleshooting",
            "infrastructure", "performance", "security", "testing", "ui", "dom", "css",
            "apis", "llm", "development", "web", "mobile", "fullstack"
        }
        skills_map = {}
        for cat_data in self.profile["skills"].values():
            for item in cat_data["items"]:
                clean_name = item.split("(")[0].strip()
                if clean_name.lower() not in GENERIC_STOP_WORDS:
                    skills_map[clean_name.lower()] = clean_name
                if item.lower() not in GENERIC_STOP_WORDS:
                    skills_map[item.lower()] = item
                if "(" in item:
                    sub_items = item.split("(")[1].replace(")", "").split(",")
                    for sub in sub_items:
                        sub_clean = sub.strip()
                        if sub_clean.lower() not in GENERIC_STOP_WORDS:
                            skills_map[sub_clean.lower()] = sub_clean

        for exp in self.profile["experience"]:
            for tag in exp.get("tags", []):
                if tag.lower() not in GENERIC_STOP_WORDS:
                    skills_map[tag.lower()] = tag
        for proj in self.profile["projects"]:
            for tag in proj.get("tags", []):
                if tag.lower() not in GENERIC_STOP_WORDS:
                    skills_map[tag.lower()] = tag

        return skills_map

    def analyze_job(self, job_title: str, job_description: str) -> Dict[str, Any]:
        """
        İlan açıklamasını ve başlığını adayın gerçek profiline göre analiz eder.
        Staj / Genç yetenek / Junior pozisyonlara öncelik verir.
        3+ veya 5+ yıl deneyim yazsa bile teknoloji uyumu yüksekse elenmez.
        """
        title_lower = job_title.lower()
        desc_lower = job_description.lower()
        combined_text = f"{title_lower} {desc_lower}"

        # 1. Kesinlikle elenmesi gereken yazılım/mühendislik dışı meslekler (Kimya, Hukuk, Tıp, Satış vb.)
        HARD_EXCLUDED_TITLES = [
            "hukuk", "legal", "lawyer", "avukat", "chemist", "kimya", "kimyager",
            "pharmacist", "eczacı", "doktor", "doctor", "hemşire", "nurse",
            "inşaat", "civil engineer", "makine mühendisi", "mechanical engineer",
            "muhasebe", "accountant", "accounting", "mali müşavir", "satış", "sales rep",
            "sales representative", "pazarlama", "marketing specialist", "insan kaynakları",
            "recruiter", "talent acquisition", "graphic designer", "ui/ux designer"
        ]
        if any(exc in title_lower for exc in HARD_EXCLUDED_TITLES):
            return {
                "match_score": 0.0,
                "matched_skills": [],
                "missing_skills": ["Alan Dışı / Yazılım Dışı Meslek"],
                "is_recommended": False,
                "is_senior": False,
                "is_intern_or_grad": False,
                "fit_summary": f"Yazılım/Sistem dışı veya hedeflenmeyen alan pozisyonu: '{job_title}'."
            }

        # 2. Adayın uzmanlık alanı dışındaki yazılım teknolojileri (.NET, Flutter, iOS vb.)
        IRRELEVANT_TECH = [
            ".net", "c#", "flutter", "ios developer", "android developer",
            "sap ", "salesforce", "abap"
        ]
        if any(irr in title_lower for irr in IRRELEVANT_TECH) and not any(k in title_lower for k in ["c++", "c ", "systems", "backend", "frontend", "web", "software", "yazılım"]):
            return {
                "match_score": 0.0,
                "matched_skills": [],
                "missing_skills": ["Alan Dışı Teknoloji (.NET/Flutter/iOS/SAP)"],
                "is_recommended": False,
                "is_senior": False,
                "is_intern_or_grad": False,
                "fit_summary": "Adayın uzmanlık alanı (Yazılım / Sistem / Web / Backend) dışındaki teknoloji yığını."
            }

        # 3. Yetenek Eşleşmesi (Tam kelime sınırı ile)
        matched_dict = {}
        for skill_key, official_name in self.candidate_skills.items():
            pattern = r'\b' + re.escape(skill_key) + r'\b'
            if re.search(pattern, combined_text):
                matched_dict[official_name] = True

        # Doğrulanmış temel teknolojiler için sınırlandırılmış regex kontrolleri
        if re.search(r'\b(typescript|ts)\b', combined_text):
            matched_dict["TypeScript"] = True
        if re.search(r'\bastro\b', combined_text):
            matched_dict["Astro"] = True
        if re.search(r'\breact native\b|react-native', combined_text):
            matched_dict["React Native"] = True
        elif re.search(r'\breact\b|\breact\.js\b', combined_text):
            matched_dict["React"] = True
        if re.search(r'\bnestjs\b|\bnest\.js\b', combined_text):
            matched_dict["NestJS"] = True
        if re.search(r'\bprisma\b', combined_text):
            matched_dict["Prisma ORM"] = True
        if re.search(r'\bsupabase\b', combined_text):
            matched_dict["Supabase"] = True
        if re.search(r'\bsocket\.io\b|\bwebsockets?\b', combined_text):
            matched_dict["Socket.IO"] = True

        matched_skills = list(matched_dict.keys())

        # Eksik teknoloji tespiti (Adayın portföyünde olmayanlar)
        COMMON_TECH_POOL = [
            "aws", "azure", "gcp", "kubernetes", "kafka", "rabbitmq", "graphql",
            "golang", "python", "rust", "angular", "vue",
            "elasticsearch", "mongodb", "terraform", "ansible"
        ]
        missing_skills = []
        for tech in COMMON_TECH_POOL:
            pattern = r'\b' + re.escape(tech) + r'\b'
            if re.search(pattern, combined_text):
                if not any(tech == k.lower() or tech in k.lower() for k in self.candidate_skills.keys()):
                    missing_skills.append(tech.upper() if len(tech) <= 4 else tech.title())

        # 3. Kıdem Seviyesi Tespiti (Senior / Lead / Intern / New Grad)
        is_senior = bool(re.search(r'\b(senior|sr|lead|principal|staff|architect|manager|director)\b', title_lower))
        is_intern_or_grad = any(k in title_lower or k in desc_lower[:400] for k in [
            "intern", "staj", "stajyer", "trainee", "talent program", 
            "genç yetenek", "graduate", "new grad", "entry level", "junior"
        ])

        # 4. Puanlama Matematiği
        title_score = 0
        if any(role in title_lower for role in ["software engineer", "yazılım", "c++", "systems", "backend", "frontend", "web", "mobile", "ai"]):
            title_score = 35
        elif any(role in title_lower for role in ["full stack", "developer", "engineer", "it support", "destek"]):
            title_score = 25

        matched_count = len(matched_skills)
        skill_score = min(matched_count * 10, 50)

        # Staj / Genç Yetenek / New Grad Bonusu (+20 Puan)
        bonus_score = 20 if is_intern_or_grad else 0

        # Senior / Kıdemli Pozisyon Düşürmesi (-20 Puan)
        senior_penalty = 20 if is_senior else 0

        # Eksik teknoloji cezası
        penalty = min(len(missing_skills) * 3, 12) + senior_penalty

        total_score = max(0.0, min(100.0, float(title_score + skill_score + bonus_score - penalty)))

        # Deneyim Yılı Notu (3+ / 5+ yıl belirtilmiş mi?)
        experience_note = ""
        has_high_exp_req = bool(re.search(r'\b(3\+|4\+|5\+|3-5|5-7)\s*(year|yıl)', combined_text))
        if is_senior or has_high_exp_req:
            experience_note = " [Kıdemli / Denenebilir İlan]"

        min_score = self.criteria.get("min_match_score", 50.0)
        is_recommended = total_score >= min_score

        if is_recommended:
            fit_summary = f"Uyumlu (%{total_score:.1f}). Eşleşenler: {', '.join(matched_skills[:4])}.{experience_note}"
        else:
            fit_summary = f"Eksik beceriler veya kıdem farkı yoğun (%{total_score:.1f}). Arananlar: {', '.join(missing_skills[:3])}."

        return {
            "match_score": round(total_score, 1),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "is_recommended": is_recommended,
            "is_senior": is_senior,
            "is_intern_or_grad": is_intern_or_grad,
            "fit_summary": fit_summary
        }

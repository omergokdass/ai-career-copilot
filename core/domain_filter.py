import re
from typing import Tuple

# Adayın kesinlikle yer almadığı teknolojiler
EXCLUDED_TECH_ROLES = [
    ".net", "c#", "dotnet", "asp.net",
    "flutter", "ios developer", "android developer", "swift", "kotlin",
    "sap ", "sap developer", "abap", "salesforce",
    "unity", "unreal engine", "game developer", "oyun geliştirici"
]

# Mühendislik / Bilişim Dışı Meslekler (Kesin Ret)
NON_IT_PROFESSIONS = [
    # Müşteri Hizmetleri & Çağrı Merkezi
    "customer service", "customer support", "customer success",
    "müşteri temsilcisi", "müşteri ilişkileri", "müşteri danışmanı",
    "müşteri deneyimi", "çağrı merkezi", "cagri merkezi", "call center",
    "şikayet yönetimi", "sikayet", "ticket officer",
    
    # Satış, Pazarlama & Finans
    "sales representative", "sales specialist", "satış temsilcisi",
    "satış uzmanı", "pazarlama", "marketing specialist", "pricing",
    "fiyatlandırma", "accountant", "muhasebe", "mali müşavir", "sigorta",
    "sales support", "satış destek",
    
    # Hukuk, Tıp, Sağlık, Doğa Bilimleri
    "legal", "avukat", "hukuk", "doctor", "doktor", "hemşire", "nurse",
    "pharmacist", "eczacı", "chemist", "kimyager", "kimya", "biyoloji",
    "bioinformatics", "genomics", "genom", "physics", "fizik",
    "mathematics expert", "matematik soru", "surgical", "cerrahi", "medbot",
    
    # İnşaat, Ziraat, Ağır Sanayi & Fiziksel Saha Bakım
    "civil engineer", "inşaat mühendisi", "makine teknikeri", "conveyor",
    "field service", "saha servis", "lazer kesim", "bodor", "ziraat",
    "gıda mühendisi", "veteriner", "çevresel sistemler", "sürdürülebilirlik",
    "esg", "karbon emisyon",
    
    # İK & Yabancı Dil Operasyonları
    "recruiter", "talent acquisition", "insan kaynakları",
    "chinese speaker", "french speaker", "german speaker", "italian speaker",
    "ai policy", "compliance analyst", "etik uyum", "ai trainer",
    
    # Üst Yönetim
    "grup direktörü", "group director", "vice president", "head of department"
]

# Pozitif Bilişim / Yazılım Rol Göstergeleri
POSITIVE_DOMAIN_KEYWORDS = [
    "software", "yazılım", "developer", "geliştirici", "engineer", "mühendis",
    "programmer", "kodlayıcı", "full stack", "fullstack",
    "backend", "frontend", "front-end", "back-end",
    "c++", "systems", "sistem", "embedded", "gömülü",
    "node", "nest", "react", "typescript", "javascript",
    "intern", "staj", "stajyer", "trainee", "genç yetenek", "graduate",
    "it support", "it destek", "bilgi işlem", "helpdesk"
]


def is_relevant_domain(title: str, description: str = "") -> Tuple[bool, str]:
    """
    İlanın bilişim/yazılım alanında olup olmadığını ve adayın odak profiliyle
    çelişip çelişmediğini inceler.
    
    Döner:
        (is_relevant: bool, reason: str)
    """
    if not title:
        return False, "İlan başlığı boş."

    title_lower = title.lower()
    desc_sample = description[:600].lower() if description else ""

    # 1. Mühendislik / Bilişim Dışı Meslek Kontrolü
    for prof in NON_IT_PROFESSIONS:
        if prof in title_lower:
            return False, f"Alan dışı / hedeflenmeyen meslek pozisyonu: '{prof}'"

    # 2. Adayın Uzmanlığı Dışındaki Yazılım Teknolojileri (.NET, C#, Flutter, iOS Native, Unity vb.)
    for tech in EXCLUDED_TECH_ROLES:
        # C++ istisnası: İlan "C++" ise ve içinde C# yoksa kabul edilir
        if tech in title_lower:
            if tech in ("c#", ".net") and "c++" in title_lower and "c#" not in title_lower and ".net" not in title_lower:
                continue
            return False, f"Adayın uzmanlığı dışındaki teknoloji yığını: '{tech}'"

    # 3. Pozitif Alan Kontrolü: Başlıkta bilişim / yazılım rolü geçiyor mu?
    has_positive_role = any(pos in title_lower for pos in POSITIVE_DOMAIN_KEYWORDS)
    if not has_positive_role:
        # Başlıkta doğrudan geçmiyorsa ilanın ilk 400 karakterine bak
        has_positive_in_desc = any(pos in desc_sample for pos in ["yazılım", "software engineer", "developer", "stajyer"])
        if not has_positive_in_desc:
            return False, f"Yazılım / Bilişim alanı ile ilgili temel unvan tespit edilemedi: '{title}'"

    return True, "Bilişim ve yazılım alanı doğrulandı."

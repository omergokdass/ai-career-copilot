from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class ReviewVerdict(str, Enum):
    RECOMMENDED = "RECOMMENDED"   # Güçlü Eşleşme (>= 65%)
    BORDERLINE = "BORDERLINE"     # Denenebilir / Sınırda (50% - 64%)
    REJECTED = "REJECTED"         # Elendi (< 50% veya alan dışı)


@dataclass
class JobPosting:
    platform: str
    title: str
    company: str
    location: str
    job_url: str
    description: str = ""
    is_easy_apply: bool = False
    
    # İnceleme sonuçları
    match_score: float = 0.0
    verdict: ReviewVerdict = ReviewVerdict.REJECTED
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    reasoning: str = ""
    highlighted_project: str = ""
    easy_apply_note: str = ""
    language: str = "tr"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "job_url": self.job_url,
            "description": self.description,
            "is_easy_apply": self.is_easy_apply,
            "match_score": self.match_score,
            "verdict": self.verdict.value,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "reasoning": self.reasoning,
            "highlighted_project": self.highlighted_project,
            "easy_apply_note": self.easy_apply_note,
            "language": self.language
        }


@dataclass
class ReviewResult:
    match_score: float
    verdict: ReviewVerdict
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    reasoning: str = ""
    highlighted_project: str = ""
    easy_apply_note: str = ""
    language: str = "tr"

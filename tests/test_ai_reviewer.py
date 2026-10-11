import unittest
from core.models import JobPosting, ReviewVerdict
from core.ai_reviewer import AIReviewer


class TestAIReviewer(unittest.TestCase):

    def setUp(self):
        self.reviewer = AIReviewer()

    def test_easy_apply_note_character_limit_guaranteed(self):
        """Kural: Easy Apply notu KESİNLİKLE <= 400 karakter olmalıdır."""
        long_note = "A" * 500
        mock_data = {
            "match_score": 85.0,
            "verdict": "RECOMMENDED",
            "matched_skills": ["C++", "Linux"],
            "missing_skills": [],
            "reasoning": "Harika uyum.",
            "highlighted_project": "Minishell",
            "easy_apply_note": long_note
        }
        job = JobPosting(platform="LinkedIn", title="C++ Dev", company="Tech", location="Istanbul", job_url="http://x")
        result = self.reviewer._parse_ai_response(mock_data, job)
        self.assertLessEqual(len(result.easy_apply_note), 400, "Not uzunluğu 400 karakteri aşamaz!")

    def test_low_score_rejected(self):
        """Kural: 50 altındaki skorlar KESİNLİKLE REJECTED olmalıdır."""
        mock_data = {
            "match_score": 35.0,
            "verdict": "RECOMMENDED",  # Model yanlışlıkla RECOMMENDED dese bile kural motoru düzeltmeli
            "matched_skills": [],
            "missing_skills": ["Java", "Spring Boot"],
            "reasoning": "Yetersiz.",
            "easy_apply_note": "Mesaj."
        }
        job = JobPosting(platform="LinkedIn", title="Java Dev", company="Tech", location="Istanbul", job_url="http://x")
        result = self.reviewer._parse_ai_response(mock_data, job)
        self.assertEqual(result.verdict, ReviewVerdict.REJECTED, "35 skorlu ilan REJECTED olmalıdır!")

    def test_heuristic_fallback_works(self):
        """API kesintisinde yerel kural motoru doğru değerlendirme yapmalıdır."""
        job = JobPosting(
            platform="LinkedIn",
            title="Junior C++ Developer",
            company="Roketsan",
            location="Istanbul",
            job_url="http://x",
            description="C++, Linux, POSIX ve bellek yönetimi bilen mühendis aranıyor."
        )
        res = self.reviewer._heuristic_review(job)
        self.assertGreaterEqual(res.match_score, 65.0)
        self.assertEqual(res.verdict, ReviewVerdict.RECOMMENDED)
        self.assertIn("C++", res.matched_skills)
        self.assertLessEqual(len(res.easy_apply_note), 400)


if __name__ == "__main__":
    unittest.main()

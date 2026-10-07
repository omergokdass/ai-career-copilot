import unittest
from core.matcher import JobMatcher
from core.ai_reviewer import AIReviewer
from run_automation import JobAutomatorOrchestrator

class TestRedesignAndFixes(unittest.TestCase):
    def setUp(self):
        self.matcher = JobMatcher()
        self.orchestrator = JobAutomatorOrchestrator()
        self.reviewer = AIReviewer()

    def test_non_software_jobs_excluded(self):
        # 1. Avient Chemist testi
        chemist_job = self.matcher.analyze_job(
            "Advanced R&D (Engnr/Chemist/Specialist)",
            "We are looking for an R&D Chemist to support polymer production lines and laboratory tests."
        )
        self.assertEqual(chemist_job["match_score"], 0.0)
        self.assertFalse(chemist_job["is_recommended"])

        # 2. Lavren Hukuk Mühendisi testi
        legal_job = self.matcher.analyze_job(
            "Hukuk Mühendisi (Legal Engineer)",
            "Şirketimizde sözleşme analizi ve hukuki süreçleri yönetecek çalışma arkadaşı arıyoruz."
        )
        self.assertEqual(legal_job["match_score"], 0.0)
        self.assertFalse(legal_job["is_recommended"])

        # 3. Satış / Muhasebe testi
        sales_job = self.matcher.analyze_job(
            "Sales Representative",
            "Responsible for managing client relations, sales quotas and marketing campaigns."
        )
        self.assertEqual(sales_job["match_score"], 0.0)
        self.assertFalse(sales_job["is_recommended"])

    def test_typescript_regex_no_false_positive(self):
        # Kelimelerin içindeki 'ts' (requirements, results) TypeScript sayılmamalı
        res = self.matcher.analyze_job(
            "Junior Software Engineer",
            "Responsibilities: Writing unit tests, delivering results, meeting client requirements."
        )
        self.assertNotIn("TypeScript", res["matched_skills"])

        # Gerçek TypeScript açıkça yazıldığında eşleşmeli
        res_ts = self.matcher.analyze_job(
            "Junior Software Engineer",
            "Requirements: Experience with TypeScript and Node.js."
        )
        self.assertIn("TypeScript", res_ts["matched_skills"])

    def test_dual_wave_full_coverage(self):
        all_queries = self.orchestrator.criteria.get("search_queries", [])
        self.assertGreaterEqual(len(all_queries), 10, "En az 10 arama sorgusu olmalı")

        # 1. Dalga (Sabah) tüm sorguları kapsamalı
        q1, label1 = self.orchestrator._select_queries_for_shift(all_queries, shift_mode="1")
        self.assertEqual(len(q1), len(all_queries), "1. Dalgada tüm kategoriler taranmalı")
        self.assertIn("1. Dalga", label1)

        # 2. Dalga (Öğle) tüm sorguları kapsamalı
        q2, label2 = self.orchestrator._select_queries_for_shift(all_queries, shift_mode="2")
        self.assertEqual(len(q2), len(all_queries), "2. Dalgada tüm kategoriler taranmalı")
        self.assertIn("2. Dalga", label2)

    def test_c_sharp_does_not_match_c_language(self):
        csharp_job = self.matcher.analyze_job(
            "Game Developer (Unity)",
            "Required skills: C#, Unity 3D, game logic, animation."
        )
        self.assertFalse(csharp_job["is_recommended"])
        self.assertNotIn("C", csharp_job["matched_skills"])

    def test_cover_letter_easy_apply_and_length_limit(self):
        # 1. Dış portal başvurusu (Easy Apply DEĞİL) -> Cover letter BOŞ olmalı
        offsite_job = {
            "title": "Junior Backend Developer",
            "company": "TechCorp",
            "description": "Looking for Node.js and PostgreSQL developer.",
            "is_easy_apply": False,
            "match_score": 80.0
        }
        res_offsite = self.reviewer._heuristic_review(offsite_job)
        self.assertEqual(res_offsite["custom_cover_letter"], "", "Dış başvurularda cover letter boş olmalı")

        # 2. Easy Apply ilanı -> Maksimum 400 karakter olmalı
        onsite_job = {
            "title": "Junior Software Engineer",
            "company": "InnovateApp",
            "description": "Looking for a React Native and NestJS junior developer.",
            "is_easy_apply": True,
            "match_score": 85.0
        }
        res_onsite = self.reviewer._heuristic_review(onsite_job)
        self.assertTrue(len(res_onsite["custom_cover_letter"]) > 0, "Easy Apply için cover letter üretilmeli")
        self.assertLessEqual(len(res_onsite["custom_cover_letter"]), 400, "Easy apply cover letter 400 karakteri geçemez!")

if __name__ == "__main__":
    unittest.main()

import unittest
from core.models import JobPosting, ReviewVerdict
from core.notifier import TelegramNotifier


class TestNotifier(unittest.TestCase):

    def setUp(self):
        self.notifier = TelegramNotifier()
        self.notifier.enabled = True
        self.notifier.bot_token = "mock_token"
        self.notifier.chat_id = "12345"

    def test_strong_vs_borderline_headers(self):
        captured_messages = []
        self.notifier.send_message = lambda text, reply_markup=None: captured_messages.append((text, reply_markup)) or True

        # 1. Güçlü İlan (75.0)
        strong_job = JobPosting(
            platform="LinkedIn",
            title="Junior Software Engineer",
            company="Google & DeepMind",
            location="Istanbul, Turkey",
            job_url="https://linkedin.com/jobs/view/999",
            match_score=75.0,
            verdict=ReviewVerdict.RECOMMENDED,
            is_easy_apply=True,
            easy_apply_note="42 İstanbul mezuniyet notu."
        )
        self.notifier.notify_job(strong_job)
        msg1, markup1 = captured_messages[0]

        self.assertIn("GÜÇLÜ EŞLEŞME YAKALANDI", msg1)
        self.assertIn("Google &amp; DeepMind", msg1, "HTML entity escape edilmeli")
        self.assertIn("<code>42 İstanbul mezuniyet notu.</code>", msg1)
        self.assertEqual(markup1["inline_keyboard"][0][0]["url"], strong_job.job_url)

        # 2. Sınırda İlan (55.0)
        border_job = JobPosting(
            platform="Kariyer.net",
            title="Backend Developer",
            company="Trendyol",
            location="Istanbul, Türkiye",
            job_url="https://kariyer.net/is-ilani/888",
            match_score=55.0,
            verdict=ReviewVerdict.BORDERLINE,
            is_easy_apply=False
        )
        self.notifier.notify_job(border_job)
        msg2, markup2 = captured_messages[1]

        self.assertNotIn("GÜÇLÜ EŞLEŞME", msg2, "55 puanlı ilana asla Güçlü Eşleşme denemez!")
        self.assertIn("DENENEBİLİR İLAN (SINIRDA)", msg2)
        self.assertIn("KARİYER.NET İLANI", msg2)


if __name__ == "__main__":
    unittest.main()

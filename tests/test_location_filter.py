import unittest
from core.location_filter import is_istanbul_location


class TestLocationFilter(unittest.TestCase):

    def test_valid_istanbul_locations(self):
        valid = [
            "Istanbul, Türkiye",
            "Istanbul, Turkey",
            "Greater Istanbul",
            "Kadıköy, Istanbul, Türkiye",
            "Beşiktaş, Istanbul, Turkey",
            "Şişli, Istanbul",
            "Ümraniye, Istanbul, Türkiye",
            "Sarıyer, Istanbul, Türkiye",
            "Maslak, Istanbul",
            "Levent, Istanbul",
            "Maltepe, Istanbul",
            "Ataşehir, Istanbul",
            "Tuzla, Istanbul",
            "Başakşehir, Istanbul"
        ]
        for loc in valid:
            ok, reason = is_istanbul_location(loc)
            self.assertTrue(ok, f"İstanbul lokasyonu kabul edilmeliydi: {loc} ({reason})")

    def test_invalid_non_istanbul_locations(self):
        invalid = [
            "Merkezefendi, Denizli, Türkiye",
            "Ergene, Tekirdağ, Türkiye",
            "Çankaya, Ankara, Türkiye",
            "Ankara, Türkiye",
            "Bornova, İzmir, Türkiye",
            "İzmir, Türkiye",
            "Bursa, Türkiye",
            "Arnavutköy, Bursa, Türkiye",
            "Gebze, Kocaeli, Türkiye",
            "Toprakkale, Osmaniye, Türkiye",
            "Antalya, Türkiye",
            "Bengaluru, Karnataka, India",
            "Montreal, Quebec, Canada",
            "Krakow, Poland"
        ]
        for loc in invalid:
            ok, reason = is_istanbul_location(loc)
            self.assertFalse(ok, f"İstanbul dışı lokasyon elenmeliydi: {loc}")

    def test_generic_undetermined_locations_rejected(self):
        generic = [
            "Türkiye",
            "Turkey",
            "Remote",
            "Turkey (Remote)",
            ""
        ]
        for loc in generic:
            ok, reason = is_istanbul_location(loc)
            self.assertFalse(ok, f"Belirsiz genel konum elenmeliydi: {loc}")

    def test_non_istanbul_city_in_title_rejected(self):
        # Başlıkta başka şehir yazıyorsa lokasyonda ne yazarsa yazsın elenmeli
        cases = [
            ("L1 IT Destek Uzmanı (15 Günlük Proje - Ergene/Tekirdağ)", "Istanbul, Türkiye"),
            ("Junior Software Engineer (Ankara)", "Istanbul, Turkey"),
            ("C++ Developer [İzmir]", "Istanbul, Türkiye"),
            ("Backend Developer - Bursa", "Istanbul, Turkey")
        ]
        for title, loc in cases:
            ok, reason = is_istanbul_location(loc, title=title)
            self.assertFalse(ok, f"Başlığında şehir olan ilan elenmeliydi: {title}")


if __name__ == "__main__":
    unittest.main()

import unittest
from core.domain_filter import is_relevant_domain


class TestDomainFilter(unittest.TestCase):

    def test_target_roles_accepted(self):
        valid_roles = [
            ("Junior Software Engineer", "Python, C++, algoritmalar."),
            ("Software Engineering Intern", "Stajyer yazılım mühendisi aranıyor."),
            ("Junior C++ Developer", "Sistem ve C++ geliştirmesi."),
            ("C++ Developer", "POSIX, Linux, multi-thread."),
            ("Junior Backend Developer", "Node.js, PostgreSQL."),
            ("Node.js Developer", "REST API, Express, NestJS."),
            ("Junior Frontend Developer", "React, TypeScript, CSS."),
            ("React Native Developer", "Mobil uygulama geliştirme."),
            ("TypeScript Developer", "Modern web ve backend."),
            ("IT Support Specialist", "Sistem destek ve ağ yönetimi.")
        ]
        for title, desc in valid_roles:
            ok, reason = is_relevant_domain(title, desc)
            self.assertTrue(ok, f"Hedef rol kabul edilmeliydi: '{title}' ({reason})")

    def test_irrelevant_professions_rejected(self):
        invalid_roles = [
            ("Pricing Specialist", "Fiyatlandırma ve maliyet analizi."),
            ("Customer Service Officer - Ticket", "Müşteri çağrı merkezi desteği."),
            ("Müşteri Başarısı & Şikayet Yönetimi Uzmanı", "Şikayet ve destek süreçleri."),
            ("DC Sales Support Engineer", "Satış teklifleri ve müşteri ziyaretleri."),
            ("Field Service Engineer - Conveyor", "Konveyör bantları mekanik saha bakım."),
            ("Technical Engineer, Surgical Robot (Medbot)", "Cerrahi ameliyat robotu donanım."),
            ("Sustainability Solutions Specialist - ESG & Carbon", "Karbon ayak izi raporlama."),
            ("Çevresel Sistemler Yönetimi Uzmanı", "Atık yönetimi ve geri dönüşüm."),
            ("Avukat / Hukuk Müşaviri", "Sözleşme ve dava yönetimi."),
            ("Biyoinformatik ve Genom Uzmanı", "DNA dizileme ve biyoloji araştırmaları."),
            ("Yapay Zeka Grup Direktörü", "15 yıl deneyimli direktör.")
        ]
        for title, desc in invalid_roles:
            ok, reason = is_relevant_domain(title, desc)
            self.assertFalse(ok, f"Alan dışı meslek elenmeliydi: '{title}'")

    def test_irrelevant_tech_rejected(self):
        # Adayın uzmanlığı dışı yazılım alanları (.NET, C#, Flutter, iOS Swift, Unity)
        excluded_techs = [
            (".NET Developer", "C# ve ASP.NET MVC."),
            ("Junior C# Developer", "Entity Framework, WinForms."),
            ("Flutter Developer", "Dart ve mobil UI."),
            ("iOS Developer", "Swift ve SwiftUI."),
            ("Unity Game Developer", "Oyun programlama C#."),
            ("SAP ABAP Developer", "Kurumsal ERP ve ABAP.")
        ]
        for title, desc in excluded_techs:
            ok, reason = is_relevant_domain(title, desc)
            self.assertFalse(ok, f"Adayın uzmanlığı dışı teknoloji elenmeliydi: '{title}'")


if __name__ == "__main__":
    unittest.main()

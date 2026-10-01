import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
SESSION_DIR = BASE_DIR / ".browser_session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

def login_and_save_session():
    print("=" * 70)
    print("🔐 LINKEDIN GÜVENLİ OTURUM KAYIT ARACI")
    print("=" * 70)
    print("Bu araç, LinkedIn hesabınıza 1 kez manuel giriş yaparak oturum çerezlerinizi")
    print(f"yerel '{SESSION_DIR.name}' klasörüne kaydedecektir.")
    print("Şifreniz koda ASLA kaydedilmez. Sadece tarayıcı oturumunuz saklanır.\n")

    with sync_playwright() as p:
        print("🌐 Chrome / Chromium tarayıcısı açılıyor...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page = context.pages[0] if context.pages else context.new_page()

        print("🔗 LinkedIn giriş sayfasına gidiliyor...")
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        print("\n" + "*" * 70)
        print("👉 LÜTFEN AÇILAN TARAYICIDA LINKEDIN HESABINIZA GİRİŞ YAPIN.")
        print("👉 (Varsa SMS / 2FA doğrulama kodunuzu girin ve ana sayfanın açılmasını bekleyin)")
        print("*" * 70)

        input("\n✅ Giriş işlemini tamamlayıp ana sayfayı gördükten sonra buraya dönüp ENTER'a basın...")

        # Oturum kontrolü
        cookies = context.cookies()
        has_li_at = any(c.get("name") == "li_at" for c in cookies)

        if has_li_at:
            print("\n🎉 BAŞARILI: 'li_at' oturum çerezi tespit edildi ve kaydedildi!")
            print(f"📁 Oturum profili: {SESSION_DIR.resolve()}")
            print("🚀 Artık botunuz bu oturumu kullanarak otomatik ve güvenle başvuru yapabilir.")
        else:
            print("\n⚠️ UYARI: Giriş tamamlanmamış olabilir (li_at çerezi bulunamadı).")
            print("Lütfen gerekirse bu aracı tekrar çalıştırıp oturumu tamamlayın.")

        time.sleep(2)
        context.close()

if __name__ == "__main__":
    login_and_save_session()

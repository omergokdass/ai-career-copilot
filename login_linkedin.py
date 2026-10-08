import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
        print("🌐 Google Chrome tarayıcısı açılıyor...", flush=True)
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            channel="chrome",
            headless=False,
            no_viewport=True,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        page = context.pages[0] if context.pages else context.new_page()

        print("🔗 LinkedIn giriş sayfasına gidiliyor...", flush=True)
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        try:
            page.bring_to_front()
        except Exception:
            pass

        print("\n" + "*" * 70)
        print("👉 LÜTFEN AÇILAN TARAYICIDA LINKEDIN HESABINIZA GİRİŞ YAPIN.")
        max_wait = 360  # 6 dakika
        start_time = time.time()
        logged_in = False
        print("⏳ Giriş yapmanız bekleniyor (Oturum açıldığında otomatik algılanacak)...")

        while time.time() - start_time < max_wait:
            time.sleep(2)
            try:
                cookies = context.cookies()
                has_li_at = any(c.get("name") == "li_at" for c in cookies)
                current_url = page.url
                if has_li_at or "feed" in current_url:
                    logged_in = True
                    break
            except Exception:
                pass

        if logged_in:
            print("\n🎉 BAŞARILI: 'li_at' oturum çerezi tespit edildi ve kaydedildi!")
            print(f"📁 Oturum profili: {SESSION_DIR.resolve()}")
            print("🔍 Şimdi profil sayfanız çekiliyor: https://www.linkedin.com/in/omergokdass ...")
            try:
                page.goto("https://www.linkedin.com/in/omergokdass", wait_until="domcontentloaded", timeout=25000)
                time.sleep(3)
                profile_html = page.content()
                profile_dump_path = BASE_DIR / "output" / "profile_dump.html"
                profile_dump_path.parent.mkdir(parents=True, exist_ok=True)
                with open(profile_dump_path, "w", encoding="utf-8") as f:
                    f.write(profile_html)
                print(f"📄 Profil içeriği başarıyla kaydedildi: {profile_dump_path}")
            except Exception as e:
                print(f"Profil sayfası kaydedilirken bilgi: {e}")
        else:
            print("\n⚠️ UYARI: Zaman aşımı - Giriş tamamlanamadı.")

        time.sleep(2)
        context.close()

if __name__ == "__main__":
    login_and_save_session()

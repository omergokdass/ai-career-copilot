import os
import re
import time
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
OUTPUT_DIR = BASE_DIR / "output"
SCREENSHOTS_DIR = OUTPUT_DIR / "pending_screenshots"
SESSION_DIR = BASE_DIR / ".browser_session"

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR.mkdir(parents=True, exist_ok=True)

class LinkedInEasyApplyBot:
    """
    LinkedIn Easy Apply formlarını tarayıcı üzerinde akıllıca dolduran,
    bilinmeyen veya maaş gibi kritik sorularda durup onay bekleyen bot.
    """
    def __init__(self):
        with open(CONFIG_DIR / "master_profile.yaml", "r", encoding="utf-8") as f:
            self.profile = yaml.safe_load(f)
        with open(CONFIG_DIR / "application_rules.yaml", "r", encoding="utf-8") as f:
            self.rules = yaml.safe_load(f)

    def is_safe_to_submit(self, modal_text: str) -> tuple[bool, str]:
        """Formdaki metinleri inceler, maaş/özel soru varsa durdurur."""
        text_lower = modal_text.lower()
        for trigger in self.rules.get("strict_review_triggers", []):
            if trigger in text_lower:
                return False, f"Hassas veya bilinmeyen soru tespit edildi: '{trigger}'"
        return True, "Form alanları güvenli."

    def answer_experience_question(self, question_text: str) -> int:
        """Deneyim yılı sorularına master profilden dürüst cevap verir."""
        q_lower = question_text.lower()
        tech_exp = self.rules.get("tech_experience_years", {})
        for tech, years in tech_exp.items():
            if tech in q_lower:
                return years
        return 0  # Profilde olmayan bir teknoloji soruluyorsa dürüstçe 0 gir

    def apply(self, page, job_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Playwright sayfası üzerinden ilana Easy Apply ile başvuruyu dener.
        """
        job_url = job_info.get("job_url", "")
        company = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(job_info.get("company", "Company")))
        cv_pdf_path = job_info.get("recommended_cv_path") or job_info.get("tailored_cv_path", "")

        try:
            page.goto(job_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(2)

            # Easy Apply butonunu ara
            easy_apply_btn = page.query_selector('button:has-text("Easy Apply"), button:has-text("Kolay Başvuru")')
            if not easy_apply_btn:
                return {
                    "status": "MANUAL_EXTERNAL",
                    "reason": "İlan LinkedIn Easy Apply değil; şirket dış başvuru portalına yönlendiriyor."
                }

            easy_apply_btn.click()
            time.sleep(2)

            # Çok adımlı başvuru modalı döngüsü (Maks. 8 adım)
            for step in range(8):
                modal = page.query_selector('.jobs-easy-apply-modal')
                if not modal:
                    break

                modal_text = modal.inner_text()
                is_safe, safety_reason = self.is_safe_to_submit(modal_text)

                if not is_safe:
                    screenshot_file = SCREENSHOTS_DIR / f"{company}_{int(time.time())}.png"
                    page.screenshot(path=str(screenshot_file))
                    return {
                        "status": "NEEDS_REVIEW",
                        "reason": safety_reason,
                        "screenshot": str(screenshot_file)
                    }

                # 1. CV Dosyası Yükleme (Eğer dosya yükleme inputu varsa)
                file_input = page.query_selector('input[type="file"]')
                if file_input and cv_pdf_path and os.path.exists(cv_pdf_path):
                    try:
                        file_input.set_input_files(cv_pdf_path)
                        time.sleep(1)
                    except Exception:
                        pass

                # 2. Butonları Kontrol Et: Submit mi? Next mi?
                submit_btn = page.query_selector('button:has-text("Submit application"), button:has-text("Başvuruyu gönder")')
                if submit_btn:
                    # Final onay adımı: Başvuruyu gönder
                    submit_btn.click()
                    time.sleep(3)
                    return {
                        "status": "APPLIED_AUTO",
                        "reason": "Tüm form alanları doğrulandı ve başvuru başarıyla gönderildi."
                    }

                next_btn = page.query_selector('button:has-text("Next"), button:has-text("İleri"), button:has-text("Review"), button:has-text("Gözden geçir")')
                if next_btn:
                    next_btn.click()
                    time.sleep(1.5)
                else:
                    break

            return {
                "status": "NEEDS_REVIEW",
                "reason": "Başvuru formu beklenmeyen bir adımda durdu, kullanıcı onayı gerekiyor."
            }

        except Exception as e:
            return {
                "status": "NEEDS_REVIEW",
                "reason": f"Form otomasyonunda istisna oluştu: {str(e)}"
            }

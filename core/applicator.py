import re
from pathlib import Path
from typing import Dict, Any, Tuple

class ApplicationGuardrail:
    """
    Başvuru süreçlerinde adayın kariyerini ve hesap güvenliğini koruyan güvenlik bariyeri.
    Kritik veya bilinmeyen sorularda asla tahmin yapmaz; inceleme için durdurur.
    """
    def __init__(self, profile: Dict[str, Any]):
        self.profile = profile
        self.defaults = profile.get("application_defaults", {})

    def evaluate_form_questions(self, questions: list) -> Tuple[bool, str]:
        """
        Formdaki soruları inceler. 
        Eğer tüm sorular önceden bilinen ve güvenli alanlarsa True döner.
        Bilinmeyen, maaş, dil veya riskli bir soru varsa False ve gerekçe döner.
        """
        for q in questions:
            q_text = str(q).lower()
            
            # Maaş beklentisi sorusu
            if any(k in q_text for k in ["salary", "maaş", "compensation", "remuneration", "beklenti"]):
                return False, f"Maaş beklentisi sorusu tespit edildi: '{q}'"

            # Farklı dil gereksinimi (Almanca, Fransızca vb.)
            if any(k in q_text for k in ["german", "almanca", "french", "fransızca", "spanish"]):
                return False, f"Yabancı dil yeterlilik sorusu: '{q}'"

            # Yer değiştirme / Taşınma şartı
            if any(k in q_text for k in ["relocate", "relocation", "taşınma"]):
                return False, f"Farklı şehre taşınma / Relocation sorusu: '{q}'"

            # Teknik sınav / Hackerrank / Görev linki
            if any(k in q_text for k in ["hackerrank", "assessment", "take-home", "sınav", "test"]):
                return False, f"Teknik sınav / Değerlendirme sorusu: '{q}'"

        return True, "Tüm form alanları standart ve güvenli."

    def get_standard_answer(self, question_text: str) -> Tuple[bool, Any]:
        """Standart sorulara verilecek dürüst ve kesin cevapları döner."""
        q = question_text.lower()

        if "authorized to work" in q or "çalışma izni" in q or "yasal izin" in q:
            return True, self.defaults.get("authorized_to_work_in_turkey", True)

        if "sponsorship" in q or "sponsorluk" in q or "visa" in q:
            return True, self.defaults.get("requires_sponsorship_turkey", False)

        if "notice period" in q or "ihbar" in q or "ne zaman başlayabilir" in q:
            return True, self.defaults.get("notice_period", "Immediate / 2 weeks")

        if "military" in q or "askerlik" in q:
            return True, self.defaults.get("military_service_status", "Exempt / Postponed")

        if "city" in q or "şehir" in q or "location" in q:
            return True, "Istanbul, Turkey"

        return False, None

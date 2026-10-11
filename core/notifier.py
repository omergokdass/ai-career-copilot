import os
import html
import requests
from typing import Dict, Any, Optional
from core.models import JobPosting, ReviewVerdict


class TelegramNotifier:
    """Telegram Bot API üzerinden zengin HTML formatlı bildirim kartları ve tek dokunuş butonları sunan motor."""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.enabled = os.getenv("TELEGRAM_ENABLED", "true").lower() in ("true", "1", "yes")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""

    def is_configured(self) -> bool:
        return bool(self.enabled and self.bot_token and self.chat_id)

    def send_message(self, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        if not self.is_configured():
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = requests.post(url, json=payload, timeout=12)
            return resp.status_code == 200 and resp.json().get("ok", False)
        except Exception as e:
            print(f"[TelegramNotifier] Gönderim hatası: {e}")
            return False

    def notify_job(self, job: JobPosting, stats: Optional[Dict[str, int]] = None) -> bool:
        """İlan için formatlanmış zengin bilgi kartı gönderir."""
        safe_company = html.escape(job.company)
        safe_title = html.escape(job.title)
        safe_loc = html.escape(job.location)
        safe_project = html.escape(job.highlighted_project or "CoupleOS & 42 Istanbul")
        safe_reason = html.escape(job.reasoning or "Teknik yetenekler ve sistem altyapısı uyumlu.")

        matched_str = html.escape(", ".join(job.matched_skills[:5])) if job.matched_skills else "Temel Yazılım Mühendisliği"
        missing_str = html.escape(", ".join(job.missing_skills[:4])) if job.missing_skills else "Kritik eksik yok"

        # Başlık ve Rozet Belirleme
        if job.match_score >= 65.0:
            header = "🎯 <b>GÜÇLÜ EŞLEŞME YAKALANDI!</b>"
        else:
            header = "💡 <b>DENENEBİLİR İLAN (SINIRDA)</b>"

        # Platform ve Kanal Rozeti
        if job.platform == "Kariyer.net":
            channel_badge = "🇹🇷 <b>KARİYER.NET İLANI</b>"
            btn_text = "🌐 Kariyer.net'te Başvur"
        elif job.is_easy_apply:
            channel_badge = "⚡ <b>LINKEDIN KOLAY BAŞVURU</b>"
            btn_text = "⚡ Kolay Başvur (LinkedIn)"
        else:
            channel_badge = "🌐 <b>ŞİRKET PORTALI BAŞVURUSU</b>"
            btn_text = "🌐 Şirket Portalında Başvur"

        stats_line = ""
        if stats:
            scanned = stats.get("scanned", 0)
            matched = stats.get("matched", 0)
            stats_line = f"📊 <i>Tarama Durumu: {scanned} incelendi | {matched} uygun bulundu</i>\n\n"

        card_body = f"""{header}
{stats_line}📌 <b>Kanal:</b> {channel_badge}
🏢 <b>Şirket:</b> {safe_company}
💼 <b>Pozisyon:</b> {safe_title}
📍 <b>Konum:</b> {safe_loc}
📊 <b>Uyum Puanı:</b> %{job.match_score:.1f}

✅ <b>Eşleşen Yetenekler:</b> {matched_str}
⚠️ <b>İlanda İstenen Ekler:</b> {missing_str}
🌟 <b>Öne Çıkarılan Proje:</b> {safe_project}
💡 <b>Değerlendirme:</b> {safe_reason}
"""

        # LinkedIn Easy Apply için 400 Karakterlik Dokun-Kopyala Notu
        note_block = ""
        if job.is_easy_apply and job.easy_apply_note:
            safe_note = html.escape(job.easy_apply_note)
            note_block = f"""
💬 <b>LinkedIn Kolay Başvuru Notu (Dokun-Kopyala / {len(job.easy_apply_note)} Karakter):</b>
<code>{safe_note}</code>
"""

        full_message = (card_body + note_block).strip()

        # Inline Buton
        reply_markup = {
            "inline_keyboard": [
                [{"text": f"🚀 {btn_text}", "url": job.job_url}]
            ]
        } if job.job_url else None

        return self.send_message(full_message, reply_markup=reply_markup)

    def notify_summary(self, scanned_count: int, matched_count: int, shift_name: str = "") -> bool:
        """Tarama döngüsü tamamlandığında tek özet raporu gönderir."""
        skipped_count = max(0, scanned_count - matched_count)
        shift_line = f"📌 <b>Vardiya:</b> {shift_name}\n" if shift_name else ""

        summary_msg = f"""🏁 <b>TARAMA DÖNGÜSÜ TAMAMLANDI</b>
{shift_line}• <b>İncelenen Yeni İlan:</b> {scanned_count}
• <b>Uygun Bulunan ve İletilen:</b> {matched_count}
• <b>Kriter Dışı (Atlanan):</b> {skipped_count}

🚀 <i>Tüm uygun fırsatlar butonlarıyla birlikte Telegram'a iletildi.</i>"""
        return self.send_message(summary_msg)

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "notifications.yaml"

class TelegramNotifier:
    """
    Kullanıcıyı Telegram üzerinden anlık ve zengin biçimlendirilmiş
    mesajlarla bilgilendiren bildirim motoru.
    """
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_PATH
        self.config = self._load_config()
        if config_path is not None:
            # Belirli bir dosya yolu verilmişse (ör: birim testlerde) o dosyanın içeriğini esas al
            self.bot_token = self.config.get("telegram", {}).get("bot_token", "").strip()
            self.chat_id = str(self.config.get("telegram", {}).get("chat_id", "")).strip()
            self.enabled = bool(self.config.get("telegram", {}).get("enabled", False) and self.bot_token and self.chat_id)
        else:
            self.bot_token = (
                os.environ.get("TELEGRAM_BOT_TOKEN") 
                or self.config.get("telegram", {}).get("bot_token", "")
            ).strip()
            self.chat_id = str(
                os.environ.get("TELEGRAM_CHAT_ID") 
                or self.config.get("telegram", {}).get("chat_id", "")
            ).strip()
            env_enabled = os.environ.get("TELEGRAM_ENABLED")
            if env_enabled is not None:
                self.enabled = env_enabled.lower() in ("true", "1", "yes")
            else:
                self.enabled = bool(self.config.get("telegram", {}).get("enabled", True))
            self.enabled = bool(self.enabled and self.bot_token and self.chat_id)
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[Notifier] Config yüklenemedi: {e}")
            return {}

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id and self.enabled)

    def send_message(self, text: str, parse_mode: str = "HTML", reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        """Telegram'a HTML veya Markdown formatında mesaj gönderir."""
        if not self.is_configured():
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("ok", False)
        except Exception as e:
            print(f"[Telegram Notifier Hatası] Mesaj gönderilemedi: {e}")
            return False

    def send_document(self, file_path: str, caption: str = "") -> bool:
        """Telegram'a dosya (PDF CV, ekran görüntüsü veya ön yazı) gönderir."""
        if not self.is_configured():
            return False

        path_obj = Path(file_path)
        if not path_obj.exists():
            return False

        # Basit multipart form-data hazırlığı
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        url = f"{self.base_url}/sendDocument"

        body = bytearray()
        # chat_id field
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{self.chat_id}\r\n'.encode("utf-8"))

        # caption field
        if caption:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode("utf-8"))

        # file field
        filename = path_obj.name
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
        with open(path_obj, "rb") as f:
            body.extend(f.read())
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        try:
            req = urllib.request.Request(
                url,
                data=bytes(body),
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("ok", False)
        except Exception as e:
            print(f"[Telegram Notifier Hatası] Doküman gönderilemedi: {e}")
            return False

    def notify_job_card(self, job_info: Dict[str, Any], category: str = "STRONG", stats: Optional[Dict[str, Any]] = None) -> bool:
        """
        İlan hakkında zenginleştirilmiş bilgi kartı, inline buton ve kopyalanabilir ön yazı gönderir.
        category: 'STRONG' (Güçlü Eşleşme) veya 'BORDERLINE' (Düşük İhtimal / Denenebilir)
        """
        import html
        company = html.escape(str(job_info.get("company", "Bilinmeyen Şirket")))
        position = html.escape(str(job_info.get("position", "Pozisyon")))
        score = job_info.get("match_score", 0.0)
        job_url = job_info.get("job_url", "")
        location = html.escape(str(job_info.get("location", "Belirtilmemiş")))
        matched_skills = job_info.get("matched_skills", [])
        missing_skills = job_info.get("missing_skills", [])
        highlighted_proj = html.escape(str(job_info.get("highlighted_project", "")))
        lang = job_info.get("language", "en").upper()
        status = job_info.get("status", "READY_TO_APPLY")

        matched_str = html.escape(", ".join(matched_skills[:6])) if matched_skills else "Genel Yazılım / Algoritma"
        missing_str = html.escape(", ".join(missing_skills[:4])) if missing_skills else "Kritik eksik yok"

        # Başvuru Kanalı Etiketi
        is_easy = (status == "READY_TO_APPLY")
        channel_badge = "⚡ <b>LINKEDIN KOLAY BAŞVURU</b>" if is_easy else "🌐 <b>ŞİRKET PORTALI / DIŞ BAŞVURU</b>"
        btn_text = "⚡ Kolay Başvur (LinkedIn)" if is_easy else "🌐 Şirket Portalında Başvur"

        is_intern = job_info.get("is_intern_or_grad", False)
        is_senior = job_info.get("is_senior", False)

        if is_intern:
            header = "🎓 <b>GENÇ YETENEK / STAJ FIRSATI</b>"
            status_desc = "Staj, mezun veya genç yetenek programı. Doğrudan senin seviyene uygun yüksek öncelikli fırsat!"
        elif is_senior:
            header = "💼 <b>KIDEMLİ / DENENEBİLİR İLAN</b>"
            status_desc = "İşveren kıdemli/deneyimli arasa da temel teknoloji yığının güçlü örtüştüğü için şansını deneyebilirsin."
        elif category == "STRONG":
            header = "🎯 <b>GÜÇLÜ EŞLEŞME YAKALANDI!</b>"
            status_desc = "Bu ilan senin doğrulanmış yeteneklerinle yüksek oranda örtüşüyor."
        else:
            header = "💡 <b>DÜŞÜK İHTİMAL / DENENEBİLİR İLAN</b>"
            status_desc = "Bazı ek teknolojiler istiyor ancak temel yazılım ve 42 altyapınla şansını deneyebilirsin."

        stats_line = ""
        if stats:
            scanned_so_far = stats.get("scanned", 0)
            matched_so_far = stats.get("matched", 0)
            stats_line = f"📊 <i>Günün Durumu: {scanned_so_far} ilan incelendi | {matched_so_far} uygun bulundu</i>\n\n"

        message = f"""{header}
{stats_line}📌 <b>Kanal:</b> {channel_badge}
🏢 <b>Şirket:</b> {company}
💼 <b>Pozisyon:</b> {position}
📍 <b>Konum:</b> {location}
📊 <b>Uyum Puanı:</b> %{score:.1f} (Dil: {lang})

✅ <b>Eşleşen Yetenekler:</b> {matched_str}
⚠️ <b>İlanda İstenen Ekler:</b> {missing_str}
🌟 <b>Öne Çıkarılan Proje:</b> {highlighted_proj or '42 Istanbul & branda.ist'}

ℹ️ <i>{status_desc}</i>
"""
        reply_markup = {
            "inline_keyboard": [
                [{"text": f"🚀 {btn_text}", "url": job_url}]
            ]
        } if job_url else None

        cl_path = job_info.get("cover_letter_path")
        cl_text = ""
        if cl_path and os.path.exists(cl_path):
            try:
                with open(cl_path, "r", encoding="utf-8") as f:
                    cl_text = f.read().strip()
            except Exception:
                pass

        if cl_text:
            safe_cl = html.escape(cl_text)
            cl_block = f"\n📋 <b>Kolay Başvuru Notu (Maks. 400 Karakter - Kopyalamak için dokunun):</b>\n<code>{safe_cl}</code>"
            if len(message + cl_block) < 3900:
                sent = self.send_message((message + cl_block).strip(), reply_markup=reply_markup)
            else:
                sent = self.send_message(message.strip(), reply_markup=reply_markup)
                cl_msg = f"📋 <b>Kolay Başvuru Notu ({lang} - Kopyalamak için dokunun):</b>\n<code>{safe_cl}</code>"
                self.send_message(cl_msg.strip())
        else:
            sent = self.send_message(message.strip(), reply_markup=reply_markup)

        return sent

    def notify_application_success(self, job_info: Dict[str, Any]) -> bool:
        """Başarılı başvuru bildirimini gönderir."""
        company = job_info.get("company", "Şirket")
        position = job_info.get("position", "Pozisyon")
        job_url = job_info.get("job_url", "")
        lang = job_info.get("language", "en").upper()

        text = f"""✅ <b>BAŞVURU TAMAMLANDI!</b>

🏢 <b>Şirket:</b> {company}
💼 <b>Pozisyon:</b> {position}
📄 <b>Kullanılan CV:</b> Omer_Faruk_Gokdas_CV_Master_ATS.pdf (English)
📝 <b>Ön Yazı:</b> {lang} Özel Cover Letter
🔗 <a href="{job_url}">Başvurulan İlanı Gör</a>
"""
        return self.send_message(text.strip())

    def notify_application_pack_ready(self, job_info: Dict[str, Any]) -> bool:
        """İlan için başvuru paketi (CV + AI Ön Yazı) hazır olduğunda bildirim gönderir."""
        company = job_info.get("company", "Şirket")
        position = job_info.get("position", "Pozisyon")
        job_url = job_info.get("job_url", "")
        lang = job_info.get("language", "en").upper()
        score = job_info.get("match_score", 0.0)

        text = f"""💼 <b>BAŞVURU PAKETİ HAZIRLANDI (%{score:.1f})</b>

🏢 <b>Şirket:</b> {company}
💼 <b>Pozisyon:</b> {position}
📄 <b>Kullanılacak CV:</b> Omer_Faruk_Gokdas_CV_Master_ATS.pdf (English)
📝 <b>Ön Yazı:</b> {lang} Özel AI Cover Letter
🔗 <a href="{job_url}">İlana Git ve Başvur</a>
"""
        return self.send_message(text.strip())

    def notify_skipped_sample(self, job_info: Dict[str, Any], reason: str) -> bool:
        """Kullanıcının botun eleme mantığını denetleyebilmesi için örnek elenen ilan gönderir."""
        import html
        company = html.escape(str(job_info.get("company", "Şirket")))
        position = html.escape(str(job_info.get("position", "Pozisyon")))
        job_url = job_info.get("job_url", "")
        score = job_info.get("match_score", 0.0)
        safe_reason = html.escape(str(reason))

        msg = f"""🚫 <b>[ÖRNEK ELENEN İLAN — TEST/DENETİM]</b>

🏢 <b>Şirket:</b> {company}
💼 <b>Pozisyon:</b> {position}
📊 <b>Uyum Puanı:</b> %{score:.1f}
❌ <b>Elenme Gerekçesi:</b> {safe_reason}

ℹ️ <i>Botun doğru filtreleme yaptığını teyit edebilmeniz için örnek olarak sunulmuştur.</i>
"""
        reply_markup = {"inline_keyboard": [[{"text": "🔍 İlanı İncele (LinkedIn)", "url": job_url}]]} if job_url else None
        return self.send_message(msg.strip(), reply_markup=reply_markup)

    def notify_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """Günün özet raporunu gönderir."""
        date_str = summary.get("date", "")
        total = summary.get("total_scanned", 0)
        applied = summary.get("applied_auto_count", summary.get("applied_auto", 0))
        review = summary.get("needs_review_count", summary.get("needs_review", 0))
        manual = summary.get("manual_external_count", 0)
        skipped = summary.get("skipped_count", summary.get("skipped", 0))

        text = f"""📊 <b>GÜNLÜK BAŞVURU VE TARAMA RAPORU</b>
📅 <b>Tarih:</b> {date_str}

• <b>Taranan Toplam İlan:</b> {total}
• <b>Otomatik Başvurulan:</b> {applied}
• <b>İnceleme / Onay Bekleyen:</b> {review}
• <b>Dış Portal / Manuel İlanlar:</b> {manual}
• <b>Elenen (Uyumsuz):</b> {skipped}

🚀 <i>Sistem aktif olarak yeni ilanları takip etmeye devam ediyor.</i>
"""
        return self.send_message(text.strip())

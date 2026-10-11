import re
from typing import Tuple

ISTANBUL_DISTRICTS = {
    "istanbul", "ıstanbul", "i̇stanbul", "greater istanbul",
    "kadıköy", "kadikoy", "beşiktaş", "besiktas", "şişli", "sisli",
    "ümraniye", "umraniye", "sarıyer", "sariyer", "maslak", "levent",
    "üsküdar", "uskudar", "ataşehir", "atasehir", "maltepe", "kartal",
    "pendik", "tuzla", "beyoğlu", "beyoglu", "fatih", "bakırköy", "bakirkoy",
    "başakşehir", "basaksehir", "beylikdüzü", "beylikduzu", "çekmeköy", "cekmekoy",
    "sancaktepe", "zeytinburnu", "kağıthane", "kagithane", "esenyurt",
    "avcılar", "avcilar", "bağcılar", "bagcilar", "güngören", "gungoren",
    "sultangazi", "eyüpsultan", "eyup", "küçükçekmece", "kucukcekmece",
    "büyükçekmece", "buyukcekmece", "silivri", "çatalca", "catalca", "şile", "sile", "adalar"
}

NON_ISTANBUL_KEYWORDS = {
    # Türkiye Şehirleri ve İlçeleri
    "ankara", "izmir", "bursa", "kocaeli", "gebze", "denizli", "tekirdağ",
    "tekirdag", "ergene", "çorlu", "corlu", "osmaniye", "antalya", "adana",
    "konya", "eskişehir", "eskisehir", "gaziantep", "kayseri", "mersin",
    "samsun", "trabzon", "sakarya", "adapazarı", "adapazari", "muğla",
    "mugla", "bodrum", "balıkesir", "balikesir", "aydın", "aydin",
    "çanakkale", "canakkale", "manisa", "kütahya", "kutahya", "edirne",
    "yalova", "bolu", "düzce", "duzce", "zonguldak", "diyarbakır",
    "diyarbakir", "hatay", "iskenderun", "malatya", "kahramanmaraş",
    "kahramanmaras", "sivas", "afyon", "afyonkarahisar", "ısparta", "isparta",
    # Yurt Dışı Şehir ve Ülkeler
    "india", "canada", "poland", "france", "brazil", "germany", "netherlands",
    "united states", "united kingdom", "london", "berlin", "amsterdam",
    "warsaw", "cracow", "krakow", "bengaluru", "bangalore", "montreal", "toronto"
}


def normalize_text(text: str) -> str:
    """Türkçe karakterleri ve küçük harfleri standartlaştırır."""
    if not text:
        return ""
    res = text.lower()
    res = res.replace("i̇", "i").replace("ı", "i").replace("I", "i").replace("İ", "i")
    return res


def is_istanbul_location(location: str, title: str = "") -> Tuple[bool, str]:
    """
    İlanın İstanbul sınırları içinde olup olmadığını doğrular.
    Başlıkta veya lokasyon açıklamasında İstanbul dışı şehir adı geçiyorsa reddeder.
    
    Döner:
        (is_valid: bool, reason: str)
    """
    if not location:
        return False, "Lokasyon bilgisi boş."

    norm_loc = normalize_text(location)
    norm_title = normalize_text(title)

    # 1. Başlıkta İstanbul dışı bir şehir açıkça belirtilmiş mi? (Örn: "IT Uzmanı (Tekirdağ)")
    for non_ist in NON_ISTANBUL_KEYWORDS:
        # Başlıkta parantez içinde veya tireyle şehir ayrılmış mı kontrol et
        if re.search(r'[\(\[\-–/]\s*' + re.escape(non_ist) + r'\b', norm_title):
            return False, f"İlan başlığında İstanbul dışı şehir belirtilmiş: '{non_ist}'"

    # 2. Lokasyonda İstanbul dışı bir şehir veya ülke geçiyor mu?
    for non_ist in NON_ISTANBUL_KEYWORDS:
        if non_ist in norm_loc:
            # "bursa" geçiyor ama lokasyonda "istanbul" da yoksa kesinlikle dışarıda
            if "istanbul" not in norm_loc:
                return False, f"İstanbul dışı lokasyon: '{non_ist}' ({location})"
            # İstisna kontrolü: "Arnavutköy, Bursa" gibi durumlar
            if f"{non_ist}" in norm_loc and norm_loc.split(",")[-1].strip() == non_ist:
                return False, f"İstanbul dışı ana lokasyon: '{non_ist}' ({location})"

    # 3. Yalnızca "Türkiye", "Turkey", "Remote" gibi belirsiz/genel konumlar
    trimmed = norm_loc.strip()
    if trimmed in ("turkiye", "turkey", "remote", "turkey (remote)", "turkiye (remote)"):
        return False, f"Belirsiz genel konum (Şehir belirtilmemiş): '{location}'"

    # 4. İstanbul veya ilçelerinden en az biri geçiyor mu?
    matched_district = None
    for d in ISTANBUL_DISTRICTS:
        norm_d = normalize_text(d)
        if norm_d in norm_loc:
            matched_district = d
            break

    if matched_district:
        return True, f"İstanbul lokasyonu doğrulandı ({matched_district})."

    return False, f"İstanbul sınırları içinde bulunamadı: '{location}'"

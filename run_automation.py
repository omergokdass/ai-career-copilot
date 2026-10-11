import sys
import argparse
from pathlib import Path

# Ortam değişkenlerini yükle (.env)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Windows terminal UTF-8 desteği
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from core.orchestrator import JobOrchestrator


def main():
    parser = argparse.ArgumentParser(description="AI Career Copilot — Otonom İş Arama & Başvuru Asistanı")
    parser.add_argument("--force", action="store_true", help="Günün taramasını zorla baştan başlat")
    parser.add_argument("--shift", default="auto", choices=["1", "2", "auto", "all"], help="Vardiya modu (1: Sabah, 2: Öğle, auto: Saat bazlı)")
    parser.add_argument("--limit", type=int, default=None, help="Sorgu başına maksimum ilan sınırı (Test amaçlı)")

    args = parser.parse_args()

    orchestrator = JobOrchestrator()
    orchestrator.run(max_per_query=args.limit, shift_mode=args.shift)


if __name__ == "__main__":
    main()

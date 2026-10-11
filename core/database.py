import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from core.models import JobPosting

DEFAULT_DB_PATH = Path(__file__).parent.parent / "applications.db"


class ApplicationDatabase:
    """SQLite tabanlı, URL tekilliği sağlayan ve tarama durumunu saklayan veritabanı yöneticisi."""
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_url TEXT UNIQUE NOT NULL,
                    platform TEXT NOT NULL,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    location TEXT,
                    match_score REAL DEFAULT 0.0,
                    verdict TEXT DEFAULT 'REJECTED',
                    status TEXT DEFAULT 'NEW',
                    is_easy_apply INTEGER DEFAULT 0,
                    matched_skills TEXT,
                    missing_skills TEXT,
                    reasoning TEXT,
                    easy_apply_note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def is_job_seen(self, job_url: str) -> bool:
        """İlanın daha önce taranıp taranmadığını kontrol eder."""
        clean_url = job_url.split("?")[0].strip()
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM applications WHERE job_url = ? OR job_url LIKE ?", 
                           (clean_url, f"{clean_url}%"))
            return cursor.fetchone() is not None

    def save_job(self, job: JobPosting, status: str = "NOTIFIED") -> int:
        """İlanı ve analiz sonuçlarını kaydeder."""
        clean_url = job.job_url.split("?")[0].strip()
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO applications (
                    job_url, platform, company, position, location,
                    match_score, verdict, status, is_easy_apply,
                    matched_skills, missing_skills, reasoning, easy_apply_note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                clean_url,
                job.platform,
                job.company,
                job.title,
                job.location,
                round(job.match_score, 1),
                job.verdict.value,
                status,
                1 if job.is_easy_apply else 0,
                json.dumps(job.matched_skills, ensure_ascii=False),
                json.dumps(job.missing_skills, ensure_ascii=False),
                job.reasoning,
                job.easy_apply_note,
                datetime.now().isoformat()
            ))
            conn.commit()
            return cursor.lastrowid

    def get_summary(self) -> Dict[str, Any]:
        """Genel veritabanı istatistiklerini döndürür."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM applications")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'NOTIFIED'")
            notified = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM applications WHERE verdict = 'RECOMMENDED'")
            recommended = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM applications WHERE verdict = 'BORDERLINE'")
            borderline = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'SKIPPED'")
            skipped = cursor.fetchone()[0]

            return {
                "total_recorded": total,
                "notified_count": notified,
                "recommended_count": recommended,
                "borderline_count": borderline,
                "skipped_count": skipped
            }

import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

DB_PATH = Path(__file__).parent.parent / "applications.db"

class ApplicationDB:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Veritabanını ve gerekli tabloları başlatır."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    job_url TEXT UNIQUE NOT NULL,
                    location TEXT,
                    platform TEXT DEFAULT 'LinkedIn',
                    match_score REAL,
                    matched_skills TEXT,
                    missing_skills TEXT,
                    tailored_cv_path TEXT,
                    cover_letter_path TEXT,
                    status TEXT DEFAULT 'NEW',
                    pending_reason TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_at TIMESTAMP
                )
            """)
            conn.commit()

    def job_exists(self, job_url: str) -> bool:
        """Bu ilanın daha önce veritabanına kaydedilip edilmediğini kontrol eder."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM applications WHERE job_url = ?", (job_url.strip(),))
            return cursor.fetchone() is not None

    def record_job(self, job_data: Dict[str, Any]) -> int:
        """Yeni bir ilanı ve analiz sonuçlarını kaydeder."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO applications (
                    company, position, job_url, location, platform,
                    match_score, matched_skills, missing_skills,
                    tailored_cv_path, cover_letter_path, status,
                    pending_reason, notes, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data.get("company", "Unknown"),
                job_data.get("position", "Unknown"),
                job_data.get("job_url", "").strip(),
                job_data.get("location", ""),
                job_data.get("platform", "LinkedIn"),
                job_data.get("match_score", 0.0),
                json.dumps(job_data.get("matched_skills", [])),
                json.dumps(job_data.get("missing_skills", [])),
                job_data.get("tailored_cv_path", ""),
                job_data.get("cover_letter_path", ""),
                job_data.get("status", "NEW"),
                job_data.get("pending_reason", ""),
                job_data.get("notes", ""),
                job_data.get("applied_at", datetime.now().isoformat() if job_data.get("status") == "APPLIED_AUTO" else None)
            ))
            conn.commit()
            return cursor.lastrowid

    def update_status(self, job_id: int, status: str, pending_reason: Optional[str] = None, notes: Optional[str] = None):
        """İlan başvuru durumunu günceller."""
        applied_at = datetime.now().isoformat() if status == "APPLIED_AUTO" else None
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE applications
                SET status = ?,
                    pending_reason = COALESCE(?, pending_reason),
                    notes = COALESCE(?, notes),
                    applied_at = CASE WHEN ? IS NOT NULL THEN ? ELSE applied_at END
                WHERE id = ?
            """, (status, pending_reason, notes, applied_at, applied_at, job_id))
            conn.commit()

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Kullanıcı girdisi veya onayı bekleyen ilanları getirir."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE status = 'NEEDS_REVIEW' ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_daily_summary(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Belirtilen güne (varsayılan bugün) ait özet istatistikleri ve başvuruları döner."""
        date_pattern = f"{date_str or datetime.now().strftime('%Y-%m-%d')}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM applications 
                WHERE created_at LIKE ? OR applied_at LIKE ?
                ORDER BY created_at DESC
            """, (date_pattern, date_pattern))
            rows = [dict(r) for r in cursor.fetchall()]

            applied = [r for r in rows if r["status"] == "APPLIED_AUTO"]
            needs_review = [r for r in rows if r["status"] == "NEEDS_REVIEW"]
            manual = [r for r in rows if r["status"] == "MANUAL_EXTERNAL"]
            skipped = [r for r in rows if r["status"] == "SKIPPED"]

            return {
                "date": date_str or datetime.now().strftime('%Y-%m-%d'),
                "total_scanned": len(rows),
                "applied_auto_count": len(applied),
                "needs_review_count": len(needs_review),
                "manual_external_count": len(manual),
                "skipped_count": len(skipped),
                "applied_jobs": applied,
                "needs_review_jobs": needs_review,
                "manual_jobs": manual
            }

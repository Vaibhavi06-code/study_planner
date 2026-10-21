"""
Database and persistent storage management using SQLite.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from .models import Subject, Task, StudySession, SpacedReview


class Storage:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            home = Path.home()
            app_dir = home / ".study_planner"
            app_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = app_dir / "study_planner.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.init_db()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self):
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Subjects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT DEFAULT 'cyan',
                    target_hours_per_week REAL DEFAULT 5.0,
                    exam_date TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT,
                    estimated_hours REAL DEFAULT 1.0,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
                )
            """)

            # Study Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER,
                    task_id INTEGER,
                    duration_minutes INTEGER NOT NULL,
                    session_type TEXT DEFAULT 'pomodoro',
                    notes TEXT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL
                )
            """)

            # Spaced Repetition items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spaced_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER,
                    topic TEXT NOT NULL,
                    repetition_count INTEGER DEFAULT 0,
                    easiness_factor REAL DEFAULT 2.5,
                    interval_days INTEGER DEFAULT 1,
                    next_review_date TEXT NOT NULL,
                    last_reviewed_at TEXT,
                    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
                )
            """)

    # --- Subject CRUD ---
    def add_subject(self, subject: Subject) -> int:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO subjects (name, color, target_hours_per_week, exam_date, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (subject.name, subject.color, subject.target_hours_per_week, subject.exam_date, subject.created_at)
            )
            return cursor.lastrowid

    def get_subjects(self) -> List[Subject]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subjects ORDER BY name ASC")
            rows = cursor.fetchall()
            return [Subject(**dict(r)) for r in rows]

    def get_subject_by_id(self, subject_id: int) -> Optional[Subject]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
            row = cursor.fetchone()
            return Subject(**dict(row)) if row else None

    def get_subject_by_name(self, name: str) -> Optional[Subject]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subjects WHERE LOWER(name) = LOWER(?)", (name.strip(),))
            row = cursor.fetchone()
            return Subject(**dict(row)) if row else None

    def delete_subject(self, subject_id: int) -> bool:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
            return cursor.rowcount > 0

    # --- Task CRUD ---
    def add_task(self, task: Task) -> int:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tasks (subject_id, title, description, due_date, estimated_hours, priority, status, completed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (task.subject_id, task.title, task.description, task.due_date, task.estimated_hours, task.priority, task.status, task.completed_at, task.created_at)
            )
            return cursor.lastrowid

    def get_tasks(self, status: Optional[str] = None, subject_id: Optional[int] = None) -> List[Task]:
        query = "SELECT * FROM tasks WHERE 1=1"
        params: List[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if subject_id:
            query += " AND subject_id = ?"
            params.append(subject_id)
        
        query += " ORDER BY CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, due_date ASC"

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [Task(**dict(r)) for r in cursor.fetchall()]

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return Task(**dict(row)) if row else None

    def update_task_status(self, task_id: int, status: str) -> bool:
        completed_at = datetime.now().isoformat() if status == "completed" else None
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
                (status, completed_at, task_id)
            )
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    # --- Study Sessions CRUD ---
    def log_session(self, session: StudySession) -> int:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO study_sessions (subject_id, task_id, duration_minutes, session_type, notes, started_at, ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session.subject_id, session.task_id, session.duration_minutes, session.session_type, session.notes, session.started_at, session.ended_at)
            )
            return cursor.lastrowid

    def get_sessions(self, limit: int = 50) -> List[StudySession]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM study_sessions ORDER BY started_at DESC LIMIT ?", (limit,))
            return [StudySession(**dict(r)) for r in cursor.fetchall()]

    # --- Spaced Repetition CRUD ---
    def add_spaced_review(self, review: SpacedReview) -> int:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO spaced_reviews (subject_id, topic, repetition_count, easiness_factor, interval_days, next_review_date, last_reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (review.subject_id, review.topic, review.repetition_count, review.easiness_factor, review.interval_days, review.next_review_date, review.last_reviewed_at)
            )
            return cursor.lastrowid

    def get_due_reviews(self, target_date: str) -> List[SpacedReview]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM spaced_reviews WHERE next_review_date <= ? ORDER BY next_review_date ASC",
                (target_date,)
            )
            return [SpacedReview(**dict(r)) for r in cursor.fetchall()]

    def get_all_reviews(self) -> List[SpacedReview]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM spaced_reviews ORDER BY next_review_date ASC")
            return [SpacedReview(**dict(r)) for r in cursor.fetchall()]

    def get_review_by_id(self, review_id: int) -> Optional[SpacedReview]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM spaced_reviews WHERE id = ?", (review_id,))
            row = cursor.fetchone()
            return SpacedReview(**dict(row)) if row else None

    def update_review(self, review: SpacedReview) -> bool:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE spaced_reviews
                SET repetition_count = ?, easiness_factor = ?, interval_days = ?, next_review_date = ?, last_reviewed_at = ?
                WHERE id = ?
                """,
                (review.repetition_count, review.easiness_factor, review.interval_days, review.next_review_date, review.last_reviewed_at, review.id)
            )
            return cursor.rowcount > 0

    # --- Export / Import ---
    def export_data(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "subjects": [s.to_dict() for s in self.get_subjects()],
            "tasks": [t.to_dict() for t in self.get_tasks()],
            "study_sessions": [s.to_dict() for s in self.get_sessions(limit=10000)],
            "spaced_reviews": [r.to_dict() for r in self.get_all_reviews()],
        }

    def import_data(self, data: Dict[str, Any]):
        for sub in data.get("subjects", []):
            try:
                self.add_subject(Subject.from_dict(sub))
            except Exception:
                pass
        for tsk in data.get("tasks", []):
            try:
                self.add_task(Task.from_dict(tsk))
            except Exception:
                pass
        for sess in data.get("study_sessions", []):
            try:
                self.log_session(StudySession.from_dict(sess))
            except Exception:
                pass
        for rev in data.get("spaced_reviews", []):
            try:
                self.add_spaced_review(SpacedReview.from_dict(rev))
            except Exception:
                pass

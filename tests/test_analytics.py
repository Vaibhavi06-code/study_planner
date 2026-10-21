"""
Unit tests for analytics and streak calculation.
"""

import unittest
import tempfile
import os
from datetime import datetime, date, timedelta
from study_planner.storage import Storage
from study_planner.analytics import Analytics
from study_planner.models import StudySession, Subject, Task


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_file.close()
        self.storage = Storage(db_path=self.temp_file.name)
        self.analytics = Analytics(self.storage)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_streak_calculation(self):
        # Empty sessions -> 0 streak
        self.assertEqual(self.analytics.get_study_streak(), 0)

        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        # Log sessions for today, yesterday, and 2 days ago
        for d in [two_days_ago, yesterday, today]:
            session = StudySession(
                duration_minutes=30,
                started_at=datetime.combine(d, datetime.min.time()).isoformat()
            )
            self.storage.log_session(session)

        self.assertEqual(self.analytics.get_study_streak(), 3)

    def test_summary_metrics(self):
        s1 = self.storage.add_subject(Subject(name="Biology"))
        t1 = self.storage.add_task(Task(subject_id=s1, title="Lab Report", status="completed"))
        t2 = self.storage.add_task(Task(subject_id=s1, title="Exam Prep", status="pending"))
        self.storage.log_session(StudySession(subject_id=s1, duration_minutes=60))

        stats = self.analytics.get_summary_stats()
        self.assertEqual(stats["total_study_hours"], 1.0)
        self.assertEqual(stats["total_tasks"], 2)
        self.assertEqual(stats["completed_tasks"], 1)
        self.assertEqual(stats["task_completion_rate"], 50.0)


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for SQLite storage layer.
"""

import unittest
import tempfile
import os
from study_planner.storage import Storage
from study_planner.models import Subject, Task, StudySession, SpacedReview


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_file.close()
        self.storage = Storage(db_path=self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_add_and_get_subjects(self):
        sub = Subject(name="Algorithms", target_hours_per_week=6.0, color="green")
        sub_id = self.storage.add_subject(sub)
        self.assertIsNotNone(sub_id)

        subjects = self.storage.get_subjects()
        self.assertEqual(len(subjects), 1)
        self.assertEqual(subjects[0].name, "Algorithms")
        self.assertEqual(subjects[0].target_hours_per_week, 6.0)

    def test_task_lifecycle(self):
        sub_id = self.storage.add_subject(Subject(name="Physics"))
        task = Task(subject_id=sub_id, title="Quantum HW", priority="high", estimated_hours=2.5)
        task_id = self.storage.add_task(task)

        # Retrieve
        t = self.storage.get_task_by_id(task_id)
        self.assertIsNotNone(t)
        self.assertEqual(t.title, "Quantum HW")
        self.assertEqual(t.status, "pending")

        # Complete
        self.storage.update_task_status(task_id, "completed")
        t_updated = self.storage.get_task_by_id(task_id)
        self.assertEqual(t_updated.status, "completed")
        self.assertIsNotNone(t_updated.completed_at)

        # Delete
        self.assertTrue(self.storage.delete_task(task_id))
        self.assertIsNone(self.storage.get_task_by_id(task_id))

    def test_log_study_session(self):
        sub_id = self.storage.add_subject(Subject(name="Chemistry"))
        session = StudySession(subject_id=sub_id, duration_minutes=50, notes="Thermodynamics")
        sess_id = self.storage.log_session(session)
        
        sessions = self.storage.get_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].duration_minutes, 50)
        self.assertEqual(sessions[0].notes, "Thermodynamics")

    def test_spaced_review_storage(self):
        rev = SpacedReview(topic="Dynamic Programming Memoization", next_review_date="2026-10-22")
        rev_id = self.storage.add_spaced_review(rev)

        all_revs = self.storage.get_all_reviews()
        self.assertEqual(len(all_revs), 1)
        self.assertEqual(all_revs[0].topic, "Dynamic Programming Memoization")


if __name__ == "__main__":
    unittest.main()

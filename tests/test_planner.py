"""
Unit tests for study planning algorithm and spaced repetition logic.
"""

import unittest
import tempfile
import os
from datetime import date, timedelta
from study_planner.storage import Storage
from study_planner.planner import Planner
from study_planner.models import Subject, Task, SpacedReview


class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_file.close()
        self.storage = Storage(db_path=self.temp_file.name)
        self.planner = Planner(self.storage)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_daily_plan_allocation(self):
        s1 = self.storage.add_subject(Subject(name="Math"))
        today_str = date.today().isoformat()
        
        # High priority task due today
        t1 = Task(subject_id=s1, title="Calculus Chapter 4", priority="high", due_date=today_str, estimated_hours=2.0)
        # Low priority task due next month
        next_month = (date.today() + timedelta(days=30)).isoformat()
        t2 = Task(subject_id=s1, title="Calculus Optional Reading", priority="low", due_date=next_month, estimated_hours=5.0)

        self.storage.add_task(t1)
        self.storage.add_task(t2)

        # Plan with max 3 hours
        plan = self.planner.generate_daily_plan(max_hours=3.0)
        self.assertEqual(len(plan["tasks"]), 1)
        self.assertEqual(plan["tasks"][0]["task"].title, "Calculus Chapter 4")
        self.assertEqual(plan["total_planned_hours"], 2.0)

    def test_spaced_repetition_progression(self):
        rev = SpacedReview(topic="Newton's Laws", easiness_factor=2.5, repetition_count=0)
        rev_id = self.storage.add_spaced_review(rev)

        # First review with quality 4 (Good)
        updated = self.planner.process_review_feedback(rev_id, quality=4)
        self.assertEqual(updated.repetition_count, 1)
        self.assertEqual(updated.interval_days, 1)

        # Second review with quality 5 (Perfect)
        updated_2 = self.planner.process_review_feedback(rev_id, quality=5)
        self.assertEqual(updated_2.repetition_count, 2)
        self.assertEqual(updated_2.interval_days, 6)

        # Failed review (quality 1) resets reps
        updated_3 = self.planner.process_review_feedback(rev_id, quality=1)
        self.assertEqual(updated_3.repetition_count, 0)
        self.assertEqual(updated_3.interval_days, 1)


if __name__ == "__main__":
    unittest.main()

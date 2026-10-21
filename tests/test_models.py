"""
Unit tests for data models and serialization.
"""

import unittest
from study_planner.models import Subject, Task, StudySession, SpacedReview


class TestModels(unittest.TestCase):
    def test_subject_to_dict_and_from_dict(self):
        s = Subject(name="Calculus", color="blue", target_hours_per_week=4.5, exam_date="2026-12-15")
        data = s.to_dict()
        self.assertEqual(data["name"], "Calculus")
        self.assertEqual(data["color"], "blue")
        self.assertEqual(data["target_hours_per_week"], 4.5)
        self.assertEqual(data["exam_date"], "2026-12-15")

        s2 = Subject.from_dict(data)
        self.assertEqual(s2.name, s.name)
        self.assertEqual(s2.target_hours_per_week, s.target_hours_per_week)

    def test_task_to_dict_and_from_dict(self):
        t = Task(title="Prepare Slides", estimated_hours=2.0, priority="urgent", due_date="2026-11-01")
        data = t.to_dict()
        self.assertEqual(data["title"], "Prepare Slides")
        self.assertEqual(data["priority"], "urgent")

        t2 = Task.from_dict(data)
        self.assertEqual(t2.title, t.title)
        self.assertEqual(t2.priority, t.priority)

    def test_spaced_review_defaults(self):
        r = SpacedReview(topic="Hash Tables")
        self.assertEqual(r.easiness_factor, 2.5)
        self.assertEqual(r.repetition_count, 0)
        self.assertEqual(r.interval_days, 1)
        self.assertIsNotNone(r.next_review_date)


if __name__ == "__main__":
    unittest.main()

"""
Study planner logic, schedule generation, and spaced repetition algorithm.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from .models import Subject, Task, SpacedReview
from .storage import Storage


class Planner:
    def __init__(self, storage: Storage):
        self.storage = storage

    def generate_daily_plan(self, target_date: Optional[str] = None, max_hours: float = 6.0) -> Dict[str, Any]:
        """
        Generates an optimized daily schedule based on task priorities, due dates,
        and subject weekly targets.
        """
        if not target_date:
            target_date = date.today().isoformat()
        
        tasks = self.storage.get_tasks(status="pending")
        due_reviews = self.storage.get_due_reviews(target_date)
        subjects = {s.id: s for s in self.storage.get_subjects()}

        # Score and sort tasks
        # Factors: Priority weight, Due date urgency
        scored_tasks = []
        for t in tasks:
            urgency_score = 0
            if t.priority == "urgent":
                urgency_score += 50
            elif t.priority == "high":
                urgency_score += 30
            elif t.priority == "medium":
                urgency_score += 15
            else:
                urgency_score += 5

            if t.due_date:
                try:
                    due = datetime.strptime(t.due_date, "%Y-%m-%d").date()
                    curr = datetime.strptime(target_date, "%Y-%m-%d").date()
                    diff = (due - curr).days
                    if diff < 0:
                        urgency_score += 100  # Overdue!
                    elif diff == 0:
                        urgency_score += 70   # Due today
                    elif diff <= 2:
                        urgency_score += 40   # Due very soon
                    elif diff <= 7:
                        urgency_score += 20   # Due this week
                except ValueError:
                    pass

            scored_tasks.append((urgency_score, t))

        scored_tasks.sort(key=lambda x: x[0], reverse=True)

        allocated_tasks = []
        allocated_hours = 0.0

        for score, task in scored_tasks:
            if allocated_hours + task.estimated_hours <= max_hours:
                sub = subjects.get(task.subject_id)
                allocated_tasks.append({
                    "task": task,
                    "subject_name": sub.name if sub else "General",
                    "subject_color": sub.color if sub else "white",
                    "allocated_hours": task.estimated_hours,
                    "urgency_score": score,
                })
                allocated_hours += task.estimated_hours

        # Reviews recommendation (15-30 mins slot)
        review_items = []
        for r in due_reviews:
            sub = subjects.get(r.subject_id)
            review_items.append({
                "review": r,
                "subject_name": sub.name if sub else "General"
            })

        return {
            "date": target_date,
            "total_planned_hours": round(allocated_hours, 1),
            "max_hours": max_hours,
            "tasks": allocated_tasks,
            "due_reviews": review_items,
        }

    def process_review_feedback(self, review_id: int, quality: int) -> SpacedReview:
        """
        Implements an enhanced SuperMemo SM-2 spaced repetition update.
        quality: 1 (Forgot completely) to 5 (Perfect recall).
        """
        review = self.storage.get_review_by_id(review_id)
        if not review:
            raise ValueError(f"Spaced review item with ID {review_id} not found.")

        # Bounds check
        quality = max(1, min(5, quality))

        # EF Calculation (SM-2)
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_ef = review.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, new_ef)  # Minimum EF floor

        if quality < 3:
            # Failed recall, reset repetition
            new_rep = 0
            new_interval = 1
        else:
            # Successful recall
            new_rep = review.repetition_count + 1
            if new_rep == 1:
                new_interval = 1
            elif new_rep == 2:
                new_interval = 6
            else:
                new_interval = max(1, int(round(review.interval_days * new_ef)))

        next_date = (date.today() + timedelta(days=new_interval)).isoformat()
        
        review.easiness_factor = round(new_ef, 2)
        review.repetition_count = new_rep
        review.interval_days = new_interval
        review.next_review_date = next_date
        review.last_reviewed_at = datetime.now().isoformat()

        self.storage.update_review(review)
        return review

    def get_exam_countdowns(self) -> List[Dict[str, Any]]:
        """Returns exams sorted by days remaining."""
        subjects = self.storage.get_subjects()
        countdowns = []
        today = date.today()

        for s in subjects:
            if s.exam_date:
                try:
                    exam_d = datetime.strptime(s.exam_date, "%Y-%m-%d").date()
                    days_left = (exam_d - today).days
                    countdowns.append({
                        "subject": s.name,
                        "exam_date": s.exam_date,
                        "days_remaining": days_left,
                        "status": "Overdue" if days_left < 0 else ("Today" if days_left == 0 else f"{days_left} days")
                    })
                except ValueError:
                    pass

        countdowns.sort(key=lambda x: x["days_remaining"])
        return countdowns

    def get_smart_recommendations(self) -> List[str]:
        """Provides actionable alerts and tips based on user's current progress."""
        recommendations = []
        today_str = date.today().isoformat()

        # Overdue tasks
        tasks = self.storage.get_tasks(status="pending")
        overdue_count = 0
        for t in tasks:
            if t.due_date and t.due_date < today_str:
                overdue_count += 1
        if overdue_count > 0:
            recommendations.append(f"⚠️ You have {overdue_count} overdue task(s). Prioritize completing them today!")

        # Due Spaced Repetitions
        due_reviews = self.storage.get_due_reviews(today_str)
        if due_reviews:
            recommendations.append(f"🧠 {len(due_reviews)} spaced review topic(s) due today for long-term retention.")

        # Upcoming exams
        exams = self.get_exam_countdowns()
        urgent_exams = [e for e in exams if 0 <= e["days_remaining"] <= 14]
        for e in urgent_exams:
            recommendations.append(f"🎯 Exam Alert: '{e['subject']}' is in {e['days_remaining']} days ({e['exam_date']}).")

        if not recommendations:
            recommendations.append("✨ All on track! Keep up your study flow.")

        return recommendations

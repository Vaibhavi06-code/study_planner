"""
Analytics, study streak calculations, and statistical reporting.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from collections import defaultdict

from .storage import Storage


class Analytics:
    def __init__(self, storage: Storage):
        self.storage = storage

    def get_study_streak(self) -> int:
        """
        Calculates consecutive study streak (days with at least 1 study session).
        """
        sessions = self.storage.get_sessions(limit=1000)
        if not sessions:
            return 0

        study_dates = set()
        for s in sessions:
            try:
                dt = datetime.fromisoformat(s.started_at).date()
                study_dates.add(dt)
            except Exception:
                pass

        if not study_dates:
            return 0

        today = date.today()
        yesterday = today - timedelta(days=1)

        # Check if user studied today or yesterday to continue streak
        current = today if today in study_dates else yesterday
        if current not in study_dates:
            return 0

        streak = 0
        while current in study_dates:
            streak += 1
            current -= timedelta(days=1)

        return streak

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Returns high-level study metrics.
        """
        sessions = self.storage.get_sessions(limit=10000)
        tasks = self.storage.get_tasks()
        subjects = self.storage.get_subjects()

        total_minutes = sum(s.duration_minutes for s in sessions)
        total_hours = round(total_minutes / 60.0, 1)
        total_sessions = len(sessions)

        completed_tasks = [t for t in tasks if t.status == "completed"]
        pending_tasks = [t for t in tasks if t.status != "completed"]
        task_completion_rate = (
            round((len(completed_tasks) / len(tasks)) * 100, 1) if tasks else 0.0
        )

        streak = self.get_study_streak()

        return {
            "total_study_hours": total_hours,
            "total_sessions": total_sessions,
            "total_tasks": len(tasks),
            "completed_tasks": len(completed_tasks),
            "pending_tasks": len(pending_tasks),
            "task_completion_rate": task_completion_rate,
            "streak_days": streak,
            "total_subjects": len(subjects),
        }

    def get_weekly_subject_progress(self) -> List[Dict[str, Any]]:
        """
        Calculates study time in the past 7 days per subject compared to their targets.
        """
        today = date.today()
        seven_days_ago = today - timedelta(days=7)

        sessions = self.storage.get_sessions(limit=1000)
        subjects = {s.id: s for s in self.storage.get_subjects()}
        
        hours_per_subject = defaultdict(float)
        for s in sessions:
            try:
                dt = datetime.fromisoformat(s.started_at).date()
                if dt >= seven_days_ago:
                    hours_per_subject[s.subject_id] += s.duration_minutes / 60.0
            except Exception:
                pass

        results = []
        for sub_id, sub in subjects.items():
            actual = round(hours_per_subject[sub_id], 1)
            target = sub.target_hours_per_week
            progress_pct = round((actual / target * 100), 1) if target > 0 else 100.0
            results.append({
                "subject_id": sub.id,
                "name": sub.name,
                "color": sub.color,
                "actual_hours": actual,
                "target_hours": target,
                "progress_pct": min(progress_pct, 100.0),
                "is_met": actual >= target,
            })

        return results

    def get_daily_activity(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Returns daily study minutes for the last N days.
        """
        today = date.today()
        start_date = today - timedelta(days=days - 1)

        sessions = self.storage.get_sessions(limit=1000)
        daily_minutes = defaultdict(int)

        for s in sessions:
            try:
                dt = datetime.fromisoformat(s.started_at).date()
                if dt >= start_date:
                    daily_minutes[dt] += s.duration_minutes
            except Exception:
                pass

        activity = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            mins = daily_minutes[d]
            activity.append({
                "date": d.isoformat(),
                "day_name": d.strftime("%a"),
                "minutes": mins,
                "hours": round(mins / 60.0, 1),
            })

        return activity

    def render_ascii_bar_chart(self, activity: List[Dict[str, Any]]) -> str:
        """Renders a simple ASCII horizontal bar chart for daily study time."""
        lines = []
        max_mins = max((a["minutes"] for a in activity), default=1)
        max_mins = max(max_mins, 60)  # at least scale to 60 mins

        for a in activity:
            bar_len = int((a["minutes"] / max_mins) * 25)
            bar = "■" * bar_len
            lines.append(f"{a['day_name']} ({a['date'][5:]}): {bar:<25} {a['hours']}h ({a['minutes']}m)")

        return "\n".join(lines)

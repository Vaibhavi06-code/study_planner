"""
Interactive terminal menu for Study Planner.
"""

import sys
from datetime import date

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .storage import Storage
from .planner import Planner
from .timer import PomodoroTimer
from .analytics import Analytics
from .models import Subject, Task, SpacedReview


def prompt(message: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    res = input(f"{message}{suffix}: ").strip()
    return res if res else default


def run_interactive_menu(storage: Storage):
    planner = Planner(storage)
    analytics = Analytics(storage)
    timer = PomodoroTimer(storage)

    while True:
        print("\n" + "=" * 45)
        print("       📚 STUDYFLOW INTERACTIVE PLANNER")
        print("=" * 45)
        print("1. 📅 View Today's Optimized Study Plan")
        print("2. ⏱️  Start Pomodoro Focus Timer")
        print("3. 📋 Manage Tasks (List, Add, Complete)")
        print("4. 📖 Manage Subjects / Courses")
        print("5. 🧠 Spaced Repetition Flash Reviews")
        print("6. 📊 Analytics, Streaks & Progress")
        print("7. 💾 Export / Backup Data")
        print("0. 🚪 Exit")
        print("-" * 45)

        choice = input("Enter choice (0-7): ").strip()

        if choice == "0":
            print("👋 Goodbye! Happy studying!")
            break

        elif choice == "1":
            print("\n--- Daily Study Plan ---")
            plan = planner.generate_daily_plan()
            recs = planner.get_smart_recommendations()
            exams = planner.get_exam_countdowns()

            if recs:
                print("\n💡 Insights:")
                for r in recs:
                    print(f"  {r}")

            if exams:
                print("\n🎯 Upcoming Exams:")
                for e in exams:
                    print(f"  • {e['subject']}: {e['status']} ({e['exam_date']})")

            tasks = plan["tasks"]
            if tasks:
                print(f"\n📋 Allocated Tasks ({plan['total_planned_hours']}h / {plan['max_hours']}h):")
                for item in tasks:
                    t = item["task"]
                    print(f"  [{t.priority.upper()}] #{t.id} {t.title} ({item['subject_name']}) - {t.estimated_hours}h")
            else:
                print("\n🎉 No pending tasks! Add tasks using option 3.")

            reviews = plan["due_reviews"]
            if reviews:
                print(f"\n🧠 Due Reviews ({len(reviews)} items):")
                for r in reviews:
                    rev = r["review"]
                    print(f"  • #{rev.id} {rev.topic} ({r['subject_name']})")

        elif choice == "2":
            print("\n--- Pomodoro Timer ---")
            mins_str = prompt("Duration in minutes", "25")
            try:
                mins = int(mins_str)
            except ValueError:
                mins = 25

            subjects = storage.get_subjects()
            sub_id = None
            if subjects:
                print("\nAvailable subjects:")
                for s in subjects:
                    print(f"  [{s.id}] {s.name}")
                sub_sel = prompt("Select Subject ID (or leave blank)", "")
                if sub_sel.isdigit():
                    sub_id = int(sub_sel)

            notes = prompt("Session notes/goals", "")
            timer.run_timer(duration_minutes=mins, subject_id=sub_id, notes=notes)

        elif choice == "3":
            print("\n--- Tasks Menu ---")
            print("a. List pending tasks")
            print("b. Add a new task")
            print("c. Mark task as completed")
            print("d. Delete a task")
            t_sub = input("Select: ").strip().lower()

            if t_sub == "a":
                tasks = storage.get_tasks(status="pending")
                subjects = {s.id: s for s in storage.get_subjects()}
                if not tasks:
                    print("No pending tasks!")
                for t in tasks:
                    sub = subjects.get(t.subject_id)
                    sub_name = sub.name if sub else "General"
                    print(f"#{t.id} [{t.priority}] {t.title} ({sub_name}) - Est: {t.estimated_hours}h - Due: {t.due_date or 'N/A'}")

            elif t_sub == "b":
                title = prompt("Task title")
                if not title:
                    print("Task title cannot be empty.")
                    continue
                subjects = storage.get_subjects()
                sub_id = None
                if subjects:
                    print("Subjects: " + ", ".join(f"[{s.id}] {s.name}" for s in subjects))
                    sid = prompt("Subject ID", "")
                    if sid.isdigit():
                        sub_id = int(sid)
                due = prompt("Due date (YYYY-MM-DD)", "")
                hours_str = prompt("Estimated hours", "1.0")
                hours = float(hours_str) if hours_str.replace(".", "", 1).isdigit() else 1.0
                prio = prompt("Priority (low, medium, high, urgent)", "medium")

                new_task = Task(
                    title=title,
                    subject_id=sub_id,
                    due_date=due if due else None,
                    estimated_hours=hours,
                    priority=prio
                )
                tid = storage.add_task(new_task)
                print(f"✅ Task created with ID #{tid}")

            elif t_sub == "c":
                tid = prompt("Enter Task ID to mark done")
                if tid.isdigit() and storage.update_task_status(int(tid), "completed"):
                    print("🎉 Task marked completed!")
                else:
                    print("❌ Task not found.")

            elif t_sub == "d":
                tid = prompt("Enter Task ID to delete")
                if tid.isdigit() and storage.delete_task(int(tid)):
                    print("🗑️  Task deleted.")
                else:
                    print("❌ Task not found.")

        elif choice == "4":
            print("\n--- Subjects Menu ---")
            print("a. List all subjects")
            print("b. Add a new subject")
            print("c. Delete a subject")
            s_sub = input("Select: ").strip().lower()

            if s_sub == "a":
                subs = storage.get_subjects()
                if not subs:
                    print("No subjects found.")
                for s in subs:
                    print(f"#{s.id} {s.name} | Weekly Target: {s.target_hours_per_week}h | Exam: {s.exam_date or 'None'}")

            elif s_sub == "b":
                name = prompt("Subject name")
                if not name:
                    print("Name cannot be empty.")
                    continue
                hrs_str = prompt("Weekly target study hours", "5.0")
                hrs = float(hrs_str) if hrs_str.replace(".", "", 1).isdigit() else 5.0
                exam = prompt("Exam date (YYYY-MM-DD)", "")
                sid = storage.add_subject(Subject(name=name, target_hours_per_week=hrs, exam_date=exam if exam else None))
                print(f"✅ Subject created with ID #{sid}")

            elif s_sub == "c":
                sid = prompt("Enter Subject ID to delete")
                if sid.isdigit() and storage.delete_subject(int(sid)):
                    print("🗑️  Subject deleted.")
                else:
                    print("❌ Subject not found.")

        elif choice == "5":
            print("\n--- Spaced Repetition Menu ---")
            print("a. View reviews due today")
            print("b. Add a new review topic")
            print("c. Practice & rate recall")
            r_sub = input("Select: ").strip().lower()

            if r_sub == "a":
                due = storage.get_due_reviews(date.today().isoformat())
                if not due:
                    print("🎉 No reviews due today! Keep learning!")
                for r in due:
                    print(f"#{r.id} Topic: {r.topic} | Interval: {r.interval_days}d | Reps: {r.repetition_count}")

            elif r_sub == "b":
                topic = prompt("Topic/concept to remember")
                if topic:
                    rid = storage.add_spaced_review(SpacedReview(topic=topic))
                    print(f"✅ Topic added with ID #{rid}")

            elif r_sub == "c":
                rid_str = prompt("Enter Review Topic ID")
                score_str = prompt("Rate recall (1=Forgot, 2=Hard, 3=Good, 4=Easy, 5=Perfect)", "3")
                if rid_str.isdigit() and score_str.isdigit():
                    try:
                        res = planner.process_review_feedback(int(rid_str), int(score_str))
                        print(f"🧠 Next review scheduled for {res.next_review_date} (in {res.interval_days} days)")
                    except Exception as e:
                        print(f"❌ Error: {e}")

        elif choice == "6":
            print("\n--- Study Analytics ---")
            stats = analytics.get_summary_stats()
            print(f"🔥 Current Streak:      {stats['streak_days']} day(s)")
            print(f"⏱️  Total Study Time:   {stats['total_study_hours']} hours across {stats['total_sessions']} sessions")
            print(f"✅ Completed Tasks:    {stats['completed_tasks']}/{stats['total_tasks']} ({stats['task_completion_rate']}%)")
            
            activity = analytics.get_daily_activity(7)
            print("\n📅 Last 7 Days Activity:")
            print(analytics.render_ascii_bar_chart(activity))

            prog = analytics.get_weekly_subject_progress()
            if prog:
                print("\n🎯 Weekly Subject Goals:")
                for p in prog:
                    check = "✅" if p["is_met"] else "⏳"
                    print(f"  {check} {p['name']}: {p['actual_hours']}h / {p['target_hours']}h ({p['progress_pct']}%)")

        elif choice == "7":
            import json
            filename = prompt("Backup file name", "study_planner_backup.json")
            data = storage.export_data()
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"✅ Backup saved to {filename}")

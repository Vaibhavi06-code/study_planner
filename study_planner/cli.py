"""
Command-line interface (CLI) for Study Planner.
Supports rich terminal formatting when 'rich' is available, with clean standard-lib fallback.
"""

import sys
import argparse
import json
from datetime import date
from typing import Optional

# Ensure UTF-8 console output on Windows to support emojis cleanly
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

from .models import Subject, Task, SpacedReview
from .storage import Storage
from .planner import Planner
from .timer import PomodoroTimer
from .analytics import Analytics


def print_header(title: str):
    if RICH_AVAILABLE:
        console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))
    else:
        print(f"\n=== {title} ===")


def main():
    parser = argparse.ArgumentParser(
        prog="study-planner",
        description="📚 StudyFlow - Intelligent Terminal Study Planner & Productivity Suite"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Subject Subcommands ---
    sub_parser = subparsers.add_parser("subject", help="Manage subjects/courses")
    sub_sub = sub_parser.add_subparsers(dest="sub_action")

    # subject add
    s_add = sub_sub.add_parser("add", help="Add a new subject")
    s_add.add_argument("name", type=str, help="Subject name (e.g., 'Data Structures')")
    s_add.add_argument("--hours", type=float, default=5.0, help="Target study hours/week")
    s_add.add_argument("--color", type=str, default="cyan", help="Display color")
    s_add.add_argument("--exam", type=str, default=None, help="Exam date (YYYY-MM-DD)")

    # subject list
    sub_sub.add_parser("list", help="List all subjects")

    # subject delete
    s_del = sub_sub.add_parser("delete", help="Delete a subject")
    s_del.add_argument("id", type=int, help="Subject ID")

    # --- Task Subcommands ---
    task_parser = subparsers.add_parser("task", help="Manage tasks and assignments")
    task_sub = task_parser.add_subparsers(dest="task_action")

    # task add
    t_add = task_sub.add_parser("add", help="Add a new study task")
    t_add.add_argument("title", type=str, help="Task title")
    t_add.add_argument("--subject", type=str, default=None, help="Subject name or ID")
    t_add.add_argument("--due", type=str, default=None, help="Due date (YYYY-MM-DD)")
    t_add.add_argument("--hours", type=float, default=1.0, help="Estimated hours")
    t_add.add_argument("--priority", choices=["low", "medium", "high", "urgent"], default="medium")
    t_add.add_argument("--desc", type=str, default="", help="Description/notes")

    # task list
    t_list = task_sub.add_parser("list", help="List tasks")
    t_list.add_argument("--status", choices=["pending", "in_progress", "completed", "all"], default="pending")
    t_list.add_argument("--subject-id", type=int, default=None)

    # task done
    t_done = task_sub.add_parser("done", help="Mark a task as completed")
    t_done.add_argument("id", type=int, help="Task ID")

    # task delete
    t_del = task_sub.add_parser("delete", help="Delete a task")
    t_del.add_argument("id", type=int, help="Task ID")

    # --- Planner / Today Command ---
    plan_parser = subparsers.add_parser("plan", help="Generate or view study plan")
    plan_parser.add_argument("--date", type=str, default=None, help="Target date (YYYY-MM-DD)")
    plan_parser.add_argument("--hours", type=float, default=6.0, help="Max study hours for the day")

    # --- Timer / Pomodoro Command ---
    timer_parser = subparsers.add_parser("timer", help="Start a Pomodoro or focus timer")
    timer_parser.add_argument("--minutes", type=int, default=25, help="Timer duration in minutes")
    timer_parser.add_argument("--subject", type=str, default=None, help="Subject name or ID")
    timer_parser.add_argument("--task-id", type=int, default=None, help="Associated Task ID")
    timer_parser.add_argument("--notes", type=str, default="", help="Notes for this session")

    # --- Spaced Repetition Subcommands ---
    review_parser = subparsers.add_parser("review", help="Spaced repetition flash topics")
    rev_sub = review_parser.add_subparsers(dest="review_action")

    # review add
    r_add = rev_sub.add_parser("add", help="Add a topic for spaced review")
    r_add.add_argument("topic", type=str, help="Topic/concept name")
    r_add.add_argument("--subject", type=str, default=None, help="Subject name or ID")

    # review list / due
    r_list = rev_sub.add_parser("due", help="Show topics due for review today")
    r_list.add_argument("--all", action="store_true", help="List all review topics")

    # review practice
    r_prac = rev_sub.add_parser("practice", help="Practice a review item")
    r_prac.add_argument("id", type=int, help="Review Item ID")
    r_prac.add_argument("quality", type=int, choices=[1, 2, 3, 4, 5], help="Recall score (1=forgot, 5=perfect)")

    # --- Stats / Dashboard ---
    subparsers.add_parser("stats", help="View study statistics, streaks & charts")

    # --- Interactive Mode ---
    subparsers.add_parser("menu", help="Launch interactive menu interface")

    # --- Export / Import ---
    exp_parser = subparsers.add_parser("export", help="Export study data to JSON")
    exp_parser.add_argument("--output", type=str, default="study_planner_backup.json", help="Output file path")

    imp_parser = subparsers.add_parser("import", help="Import study data from JSON")
    imp_parser.add_argument("file", type=str, help="JSON file path to import")

    args = parser.parse_args()

    # If no arguments provided, launch interactive menu
    if not args.command:
        from .interactive import run_interactive_menu
        storage = Storage()
        run_interactive_menu(storage)
        return

    storage = Storage()
    planner = Planner(storage)
    analytics = Analytics(storage)

    # --- Handlers ---
    if args.command == "subject":
        handle_subject(args, storage)
    elif args.command == "task":
        handle_task(args, storage)
    elif args.command == "plan":
        handle_plan(args, storage, planner)
    elif args.command == "timer":
        handle_timer(args, storage)
    elif args.command == "review":
        handle_review(args, storage, planner)
    elif args.command == "stats":
        handle_stats(storage, analytics)
    elif args.command == "menu":
        from .interactive import run_interactive_menu
        run_interactive_menu(storage)
    elif args.command == "export":
        data = storage.export_data()
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Data exported successfully to {args.output}")
    elif args.command == "import":
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
        storage.import_data(data)
        print(f"✅ Data imported successfully from {args.file}")


def resolve_subject_id(storage: Storage, identifier: Optional[str]) -> Optional[int]:
    if not identifier:
        return None
    if identifier.isdigit():
        return int(identifier)
    sub = storage.get_subject_by_name(identifier)
    return sub.id if sub else None


def handle_subject(args, storage: Storage):
    if args.sub_action == "add":
        sub = Subject(
            name=args.name,
            target_hours_per_week=args.hours,
            color=args.color,
            exam_date=args.exam
        )
        try:
            sub_id = storage.add_subject(sub)
            print(f"✅ Subject '{args.name}' added with ID: {sub_id}")
        except Exception as e:
            print(f"❌ Error adding subject: {e}")

    elif args.sub_action == "delete":
        if storage.delete_subject(args.id):
            print(f"🗑️  Subject #{args.id} deleted.")
        else:
            print(f"❌ Subject #{args.id} not found.")

    else:  # list
        subjects = storage.get_subjects()
        if not subjects:
            print("No subjects found. Add one with: study-planner subject add <name>")
            return

        if RICH_AVAILABLE:
            table = Table(title="📖 Subjects & Courses")
            table.add_column("ID", style="dim", width=6)
            table.add_column("Name", style="bold")
            table.add_column("Target Hrs/Wk", justify="right")
            table.add_column("Exam Date")
            for s in subjects:
                table.add_row(
                    str(s.id),
                    f"[{s.color}]{s.name}[/{s.color}]",
                    f"{s.target_hours_per_week}h",
                    s.exam_date or "None"
                )
            console.print(table)
        else:
            print_header("Subjects & Courses")
            for s in subjects:
                print(f"[{s.id}] {s.name} - Target: {s.target_hours_per_week}h/wk | Exam: {s.exam_date or 'N/A'}")


def handle_task(args, storage: Storage):
    if args.task_action == "add":
        sub_id = resolve_subject_id(storage, args.subject)
        task = Task(
            subject_id=sub_id,
            title=args.title,
            description=args.desc,
            due_date=args.due,
            estimated_hours=args.hours,
            priority=args.priority
        )
        task_id = storage.add_task(task)
        print(f"✅ Task '{args.title}' added with ID: {task_id}")

    elif args.task_action == "done":
        if storage.update_task_status(args.id, "completed"):
            print(f"🎉 Task #{args.id} marked as completed!")
        else:
            print(f"❌ Task #{args.id} not found.")

    elif args.task_action == "delete":
        if storage.delete_task(args.id):
            print(f"🗑️  Task #{args.id} deleted.")
        else:
            print(f"❌ Task #{args.id} not found.")

    else:  # list
        filter_status = None if args.status == "all" else args.status
        tasks = storage.get_tasks(status=filter_status, subject_id=args.subject_id)
        subjects = {s.id: s for s in storage.get_subjects()}

        if not tasks:
            print("No tasks found matching criteria.")
            return

        if RICH_AVAILABLE:
            table = Table(title=f"📋 Tasks ({args.status.upper()})")
            table.add_column("ID", width=6)
            table.add_column("Title", style="bold")
            table.add_column("Subject")
            table.add_column("Priority")
            table.add_column("Est. Hours", justify="right")
            table.add_column("Due Date")
            table.add_column("Status")

            priority_colors = {"urgent": "bold red", "high": "red", "medium": "yellow", "low": "green"}
            for t in tasks:
                sub = subjects.get(t.subject_id)
                sub_name = f"[{sub.color}]{sub.name}[/{sub.color}]" if sub else "General"
                color = priority_colors.get(t.priority, "white")
                table.add_row(
                    str(t.id),
                    t.title,
                    sub_name,
                    f"[{color}]{t.priority}[/{color}]",
                    f"{t.estimated_hours}h",
                    t.due_date or "-",
                    f"[green]✓ Done[/green]" if t.status == "completed" else t.status
                )
            console.print(table)
        else:
            print_header(f"Tasks ({args.status})")
            for t in tasks:
                sub = subjects.get(t.subject_id)
                sub_name = sub.name if sub else "General"
                status_icon = "✓" if t.status == "completed" else "○"
                print(f"[{status_icon}] #{t.id} {t.title} | {sub_name} | Priority: {t.priority} | Due: {t.due_date or '-'} | {t.estimated_hours}h")


def handle_plan(args, storage: Storage, planner: Planner):
    plan_date = args.date or date.today().isoformat()
    plan = planner.generate_daily_plan(target_date=plan_date, max_hours=args.hours)
    recommendations = planner.get_smart_recommendations()
    countdowns = planner.get_exam_countdowns()

    print_header(f"📅 Study Plan for {plan_date}")
    
    if recommendations:
        print("\n💡 Insights & Recommendations:")
        for r in recommendations:
            print(f"  {r}")

    if countdowns:
        print("\n🎯 Exam Countdowns:")
        for c in countdowns:
            print(f"  • {c['subject']}: {c['status']} ({c['exam_date']})")

    tasks = plan["tasks"]
    if tasks:
        print(f"\n📋 Allocated Tasks (Planned: {plan['total_planned_hours']}h / Max: {plan['max_hours']}h):")
        for item in tasks:
            t = item["task"]
            print(f"  [{t.priority.upper()}] #{t.id} {t.title} ({item['subject_name']}) - {t.estimated_hours}h (Due: {t.due_date or 'None'})")
    else:
        print("\n🎉 No pending tasks found for today's plan!")

    reviews = plan["due_reviews"]
    if reviews:
        print(f"\n🧠 Spaced Repetition Due Today ({len(reviews)} items):")
        for r in reviews:
            rev = r["review"]
            print(f"  • #{rev.id} {rev.topic} ({r['subject_name']}) - Repetition: {rev.repetition_count}")


def handle_timer(args, storage: Storage):
    timer = PomodoroTimer(storage)
    sub_id = resolve_subject_id(storage, args.subject)
    timer.run_timer(
        duration_minutes=args.minutes,
        label="Pomodoro Focus Session",
        subject_id=sub_id,
        task_id=args.task_id,
        notes=args.notes
    )


def handle_review(args, storage: Storage, planner: Planner):
    if args.review_action == "add":
        sub_id = resolve_subject_id(storage, args.subject)
        rev = SpacedReview(
            subject_id=sub_id,
            topic=args.topic,
            next_review_date=date.today().isoformat()
        )
        rev_id = storage.add_spaced_review(rev)
        print(f"✅ Topic '{args.topic}' added for spaced repetition (ID: {rev_id}).")

    elif args.review_action == "practice":
        try:
            updated = planner.process_review_feedback(args.id, args.quality)
            print(f"🧠 Review recorded! Next review scheduled for: {updated.next_review_date} (Interval: {updated.interval_days} day(s))")
        except ValueError as e:
            print(f"❌ {e}")

    else:  # due or list
        if getattr(args, "all", False):
            reviews = storage.get_all_reviews()
            title = "All Spaced Repetition Topics"
        else:
            reviews = storage.get_due_reviews(date.today().isoformat())
            title = "🧠 Due Reviews Today"

        if not reviews:
            print("No review items due!")
            return

        print_header(title)
        subjects = {s.id: s for s in storage.get_subjects()}
        for r in reviews:
            sub = subjects.get(r.subject_id)
            sub_name = sub.name if sub else "General"
            print(f"#{r.id} | Topic: {r.topic} | Course: {sub_name} | Due: {r.next_review_date} | Reps: {r.repetition_count}")
        print("\nRate your recall after reviewing: study-planner review practice <ID> <1-5>")


def handle_stats(storage: Storage, analytics: Analytics):
    stats = analytics.get_summary_stats()
    weekly_prog = analytics.get_weekly_subject_progress()
    activity = analytics.get_daily_activity(7)

    print_header("📊 Study Analytics & Dashboard")
    print(f"🔥 Study Streak:        {stats['streak_days']} day(s)")
    print(f"⏱️  Total Study Time:    {stats['total_study_hours']} hours across {stats['total_sessions']} sessions")
    print(f"✅ Task Completion:     {stats['completed_tasks']}/{stats['total_tasks']} ({stats['task_completion_rate']}%)")
    print(f"📚 Active Subjects:     {stats['total_subjects']}")

    print("\n📅 7-Day Study Activity:")
    print(analytics.render_ascii_bar_chart(activity))

    if weekly_prog:
        print("\n🎯 Weekly Subject Targets:")
        for p in weekly_prog:
            status_icon = "✅" if p["is_met"] else "⏳"
            print(f"  {status_icon} {p['name']:<18} {p['actual_hours']:>4.1f}h / {p['target_hours']}h ({p['progress_pct']}%)")


if __name__ == "__main__":
    main()

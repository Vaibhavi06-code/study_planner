"""
Interactive Pomodoro timer and study session logger.
"""

import sys
import time
from datetime import datetime
from typing import Optional

from .models import StudySession
from .storage import Storage


class PomodoroTimer:
    def __init__(self, storage: Storage):
        self.storage = storage

    def format_time(self, seconds: int) -> str:
        mins, secs = divmod(seconds, 60)
        return f"{mins:02d}:{secs:02d}"

    def run_timer(
        self,
        duration_minutes: int = 25,
        label: str = "Focus Session",
        subject_id: Optional[int] = None,
        task_id: Optional[int] = None,
        notes: str = "",
        session_type: str = "pomodoro"
    ) -> bool:
        """
        Runs a live terminal timer with a visual progress bar.
        Returns True if session completed successfully, False if aborted.
        """
        total_seconds = duration_minutes * 60
        started_at = datetime.now().isoformat()
        
        print(f"\n🍅 Starting {label} for {duration_minutes} minutes...")
        print("Press Ctrl+C at any time to pause or end early.\n")

        try:
            for elapsed in range(total_seconds + 1):
                remaining = total_seconds - elapsed
                percent = (elapsed / total_seconds) * 100
                bar_length = 30
                filled = int(bar_length * elapsed // total_seconds)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                sys.stdout.write(
                    f"\r\033[K[{bar}] {percent:5.1f}% | ⏳ Left: {self.format_time(remaining)} | Elapsed: {self.format_time(elapsed)}"
                )
                sys.stdout.flush()
                
                if elapsed < total_seconds:
                    time.sleep(1)

            print("\n\n🎉 Great job! Session completed!")
            # Terminal bell / beep notification
            sys.stdout.write("\a")
            sys.stdout.flush()

            # Log to DB
            session = StudySession(
                subject_id=subject_id,
                task_id=task_id,
                duration_minutes=duration_minutes,
                session_type=session_type,
                notes=notes,
                started_at=started_at,
                ended_at=datetime.now().isoformat()
            )
            sess_id = self.storage.log_session(session)
            print(f"📝 Study session logged successfully (ID: {sess_id}).")
            return True

        except KeyboardInterrupt:
            print("\n\n⏸️  Timer paused / stopped.")
            elapsed_mins = max(1, elapsed // 60)
            if elapsed_mins > 0:
                choice = input(f"Would you like to save the {elapsed_mins} minutes studied? [y/N]: ").strip().lower()
                if choice in ("y", "yes"):
                    session = StudySession(
                        subject_id=subject_id,
                        task_id=task_id,
                        duration_minutes=elapsed_mins,
                        session_type=session_type,
                        notes=f"{notes} (interrupted)",
                        started_at=started_at,
                        ended_at=datetime.now().isoformat()
                    )
                    sess_id = self.storage.log_session(session)
                    print(f"📝 Partial study session ({elapsed_mins} min) logged (ID: {sess_id}).")
            return False

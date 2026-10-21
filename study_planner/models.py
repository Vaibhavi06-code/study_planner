"""
Data models for Study Planner.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional, List, Dict, Any


@dataclass
class Subject:
    id: Optional[int] = None
    name: str = ""
    color: str = "cyan"
    target_hours_per_week: float = 5.0
    exam_date: Optional[str] = None  # Format: YYYY-MM-DD
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Subject":
        return cls(**data)


@dataclass
class Task:
    id: Optional[int] = None
    subject_id: Optional[int] = None
    title: str = ""
    description: str = ""
    due_date: Optional[str] = None  # Format: YYYY-MM-DD
    estimated_hours: float = 1.0
    priority: str = "medium"  # low, medium, high, urgent
    status: str = "pending"  # pending, in_progress, completed
    completed_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(**data)


@dataclass
class StudySession:
    id: Optional[int] = None
    subject_id: Optional[int] = None
    task_id: Optional[int] = None
    duration_minutes: int = 25
    session_type: str = "pomodoro"  # pomodoro, free, revision
    notes: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudySession":
        return cls(**data)


@dataclass
class SpacedReview:
    id: Optional[int] = None
    subject_id: Optional[int] = None
    topic: str = ""
    repetition_count: int = 0
    easiness_factor: float = 2.5
    interval_days: int = 1
    next_review_date: str = field(default_factory=lambda: date.today().isoformat())
    last_reviewed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpacedReview":
        return cls(**data)

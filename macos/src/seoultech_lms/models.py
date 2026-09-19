from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Course:
    id: str
    name: str
    professor: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class Notice:
    id: str
    course_id: str
    title: str
    content: str | None = None
    created_at: datetime | None = None
    url: str | None = None


@dataclass(frozen=True)
class Assignment:
    id: str
    course_id: str
    title: str
    description: str | None = None
    due_at: datetime | None = None
    submitted: bool | None = None
    url: str | None = None


@dataclass(frozen=True)
class Material:
    id: str
    course_id: str
    title: str
    created_at: datetime | None = None
    url: str | None = None


def as_jsonable(value: Any) -> dict[str, Any]:
    result = asdict(value)
    return {key: item.isoformat() if isinstance(item, datetime) else item for key, item in result.items()}

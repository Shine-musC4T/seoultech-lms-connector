from __future__ import annotations

from datetime import datetime, timedelta

from .models import Assignment


def pending_assignments(assignments: list[Assignment]) -> list[Assignment]:
    """Return assignments not known to be submitted, ordered by deadline."""
    pending = [item for item in assignments if item.submitted is not True]
    return sorted(pending, key=lambda item: (item.due_at is None, item.due_at or datetime.max, item.title))


def upcoming_deadlines(
    assignments: list[Assignment],
    *,
    days: int = 7,
    now: datetime | None = None,
) -> list[Assignment]:
    """Return unsubmitted assignments due from now through the requested horizon."""
    if days < 0:
        raise ValueError("days는 0 이상이어야 합니다.")
    start = now or datetime.now()
    end = start + timedelta(days=days)
    return [item for item in pending_assignments(assignments) if item.due_at and start <= item.due_at <= end]

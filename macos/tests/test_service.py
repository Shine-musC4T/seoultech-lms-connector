from __future__ import annotations

import unittest
from datetime import datetime

from seoultech_lms.models import Assignment
from seoultech_lms.service import pending_assignments, upcoming_deadlines


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 17, 12, 0)
        self.assignments = [
            Assignment("done", "c1", "완료", due_at=datetime(2026, 9, 18), submitted=True),
            Assignment("late", "c1", "지남", due_at=datetime(2026, 9, 16), submitted=False),
            Assignment("soon", "c2", "임박", due_at=datetime(2026, 9, 20), submitted=False),
            Assignment("later", "c2", "나중", due_at=datetime(2026, 10, 1), submitted=None),
        ]

    def test_pending_excludes_submitted_and_sorts_by_due_date(self) -> None:
        self.assertEqual([item.id for item in pending_assignments(self.assignments)], ["late", "soon", "later"])

    def test_upcoming_excludes_overdue_and_outside_horizon(self) -> None:
        result = upcoming_deadlines(self.assignments, days=7, now=self.now)
        self.assertEqual([item.id for item in result], ["soon"])

    def test_negative_horizon_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            upcoming_deadlines(self.assignments, days=-1, now=self.now)


if __name__ == "__main__":
    unittest.main()

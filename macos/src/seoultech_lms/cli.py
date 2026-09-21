from __future__ import annotations

import argparse
import asyncio
import json
import sys

from . import __version__
from .auth import AuthenticationRequired, auth_state_path
from .browser import interactive_login
from .client import ReadOnlyViolation, SeoultechLMSClient
from .models import Assignment, Course, Notice, as_jsonable
from .service import pending_assignments, upcoming_deadlines


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only SeoulTech LMS connector")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("login", help="브라우저에서 직접 로그인하고 로컬 세션 저장")
    subparsers.add_parser("logout", help="로컬에 저장된 로그인 세션 삭제")
    subparsers.add_parser("doctor", help="설치와 로그인 세션 상태 점검")

    for name, help_text in (
        ("courses", "현재 수강 과목 조회"),
        ("notices", "공지 목록 조회"),
        ("assignments", "과제 목록 조회"),
        ("pending", "미제출 과제 조회"),
        ("deadlines", "지정한 기간 안에 마감되는 미제출 과제 조회"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        if name != "courses":
            command.add_argument("--course-id")
        if name == "deadlines":
            command.add_argument("--days", type=int, default=7)
        command.add_argument("--json", action="store_true")
    return parser


async def _query(args: argparse.Namespace) -> list[Course] | list[Notice] | list[Assignment]:
    async with SeoultechLMSClient() as client:
        if args.command == "courses":
            return await client.get_courses()
        if args.command == "notices":
            return await client.get_notices(args.course_id)
        assignments = await client.get_assignments(
            args.course_id,
            include_completed=args.command not in ("pending", "deadlines"),
        )
        if args.command == "pending":
            return pending_assignments(assignments)
        if args.command == "deadlines":
            return upcoming_deadlines(assignments, days=args.days)
        return assignments


async def _doctor() -> int:
    state_path = auth_state_path()
    if not state_path.is_file():
        print("[실패] 로그인 세션 없음")
        print("실행: seoultech-lms login")
        return 2
    async with SeoultechLMSClient() as client:
        courses = await client.get_courses()
    print(f"[정상] 설치됨: {__version__}")
    print(f"[정상] 로그인 세션 유효, 수강 과목 {len(courses)}개 조회")
    print(f"[정보] 세션 위치: {state_path}")
    return 0


def _print_result(command: str, result: list[Course] | list[Notice] | list[Assignment]) -> None:
    if command == "courses":
        for index, course in enumerate(result, 1):
            assert isinstance(course, Course)
            professor = f" — {course.professor}" if course.professor else ""
            print(f"[{index}] {course.name}{professor}\n    ID: {course.id}")
    elif command == "notices":
        for index, notice in enumerate(result, 1):
            assert isinstance(notice, Notice)
            created = notice.created_at.strftime("%Y-%m-%d %H:%M") if notice.created_at else "게시일 미제공"
            print(f"[{index}] {notice.title}\n    과목 ID: {notice.course_id} | 게시일: {created}")
    else:
        for index, assignment in enumerate(result, 1):
            assert isinstance(assignment, Assignment)
            due = assignment.due_at.strftime("%Y-%m-%d %H:%M") if assignment.due_at else "마감일 미제공"
            state = "제출" if assignment.submitted is True else "미제출" if assignment.submitted is False else "제출 여부 미제공"
            print(f"[{index}] {assignment.title}\n    과목 ID: {assignment.course_id} | {due} | {state}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = _build_parser()
    args = parser.parse_args()

    try:
        if args.command == "login":
            state_path = auth_state_path()
            asyncio.run(interactive_login(state_path))
            print(f"로그인 세션을 저장했습니다: {state_path}")
            return
        if args.command == "logout":
            state_path = auth_state_path()
            if state_path.exists():
                state_path.unlink()
                print(f"로그인 세션을 삭제했습니다: {state_path}")
            else:
                print("저장된 로그인 세션이 없습니다.")
            return
        if args.command == "doctor":
            raise SystemExit(asyncio.run(_doctor()))
        result = asyncio.run(_query(args))
    except (AuthenticationRequired, ReadOnlyViolation, RuntimeError, ValueError) as exc:
        parser.exit(2, f"오류: {exc}\n")

    if args.json:
        print(json.dumps([as_jsonable(item) for item in result], ensure_ascii=False, indent=2))
    else:
        _print_result(args.command, result)


if __name__ == "__main__":
    main()

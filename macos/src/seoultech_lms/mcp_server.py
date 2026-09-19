from __future__ import annotations

import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .auth import auth_state_path
from .browser import start_login_browser
from .client import SeoultechLMSClient
from .models import as_jsonable
from .service import pending_assignments, upcoming_deadlines


mcp = FastMCP(
    "seoultech_c4t",
    instructions=(
        "이 서버는 사용자 컴퓨터에서 'python -m seoultech_lms.mcp_server'로 실행되는 로컬 stdio MCP다. "
        "호스트 AI 클라이언트가 로컬 프로세스와 로컬 인증 상태에 접근할 수 있어야 한다. "
        "서울과학기술대학교 e-Class의 로그인한 사용자 데이터를 읽기 전용으로 조회한다. "
        "로그인 도구는 'python -m seoultech_lms.login_window'를 로컬에서 실행해 공식 LMS 로그인 페이지를 Chrome으로 열고 인증 상태만 로컬에 저장한다. "
        "과제 제출, 게시물 작성, 수정, 삭제, 파일 업로드는 지원하지 않는다."
    ),
)


def _json_list(items: list[Any]) -> list[dict[str, Any]]:
    return [as_jsonable(item) for item in items]


def _with_course_names(items: list[Any], course_names: dict[str, str]) -> list[dict[str, Any]]:
    results = _json_list(items)
    for result in results:
        result["course_name"] = course_names.get(str(result.get("course_id")))
    return results


@mcp.tool()
def start_login() -> dict[str, str]:
    """로그인 세션이 없거나 만료됐을 때 사용자가 직접 로그인할 Chrome 창을 연다."""
    return start_login_browser(auth_state_path())


@mcp.tool()
async def list_courses() -> list[dict[str, Any]]:
    """현재 수강 중인 과목 목록을 조회한다."""
    async with SeoultechLMSClient() as client:
        return _json_list(await client.get_courses())


@mcp.tool()
async def list_notices(
    course_id: str | None = None,
    include_content: bool = True,
) -> list[dict[str, Any]]:
    """전체 과목 또는 지정한 과목의 공지 목록, 게시일과 전체 본문을 조회한다."""
    async with SeoultechLMSClient() as client:
        courses = await client.get_courses()
        notices = await client.get_notices(course_id, include_content=include_content)
    return _with_course_names(notices, {course.id: course.name for course in courses})


@mcp.tool()
async def search_notices(
    query: str,
    course_id: str | None = None,
) -> list[dict[str, Any]]:
    """공지 전체 본문에서 검색하고 각 결과의 게시일도 함께 반환한다."""
    normalized_query = query.strip().casefold()
    if not normalized_query:
        raise ValueError("검색어를 입력해주세요.")
    async with SeoultechLMSClient() as client:
        courses = await client.get_courses()
        notices = await client.get_notices(course_id, include_content=True)
    matched = [
        notice
        for notice in notices
        if normalized_query in f"{notice.title}\n{notice.content or ''}".casefold()
    ]
    return _with_course_names(matched, {course.id: course.name for course in courses})


@mcp.tool()
async def list_assignments(
    course_id: str | None = None,
    include_completed: bool = False,
) -> list[dict[str, Any]]:
    """전체 과목 또는 지정한 과목의 과제, 마감일, 제출 여부를 조회한다."""
    async with SeoultechLMSClient() as client:
        courses = await client.get_courses()
        assignments = await client.get_assignments(course_id, include_completed=include_completed)
    return _with_course_names(assignments, {course.id: course.name for course in courses})


@mcp.tool()
async def get_pending_assignments(course_id: str | None = None) -> list[dict[str, Any]]:
    """현재 미제출이거나 제출 여부가 확인되지 않은 과제를 마감일 순으로 조회한다."""
    async with SeoultechLMSClient() as client:
        courses = await client.get_courses()
        assignments = await client.get_assignments(course_id, include_completed=False)
    return _with_course_names(
        pending_assignments(assignments),
        {course.id: course.name for course in courses},
    )


@mcp.tool()
async def get_upcoming_deadlines(
    days: int = 7,
    course_id: str | None = None,
) -> list[dict[str, Any]]:
    """오늘부터 지정한 일수 안에 마감되는 미제출 과제를 조회한다."""
    async with SeoultechLMSClient() as client:
        courses = await client.get_courses()
        assignments = await client.get_assignments(course_id, include_completed=False)
    return _with_course_names(
        upcoming_deadlines(assignments, days=days),
        {course.id: course.name for course in courses},
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

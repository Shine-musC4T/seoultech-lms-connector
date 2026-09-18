"""Parsers for the verified server-rendered and AJAX HTML structures."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import urlencode

from bs4 import BeautifulSoup, Tag

from .endpoints import ACTIVITY_FORM, COURSE_HOME, NOTICE_FORM, absolute
from .models import Assignment, Course, Notice

_COURSE_ID = re.compile(r"eclassRoom\(['\"]([^'\"]+)['\"]")
_PROFESSOR = re.compile(r"\d{6}-\d{5}\s+(.+?)\s+(?:월|화|수|목|금|토|일)\s*\(")
_KOREAN_DATETIME = re.compile(
    r"(?P<year>\d{4})[.-](?P<month>\d{1,2})[.-](?P<day>\d{1,2})"
    r"(?:\s*\([^)]*\))?\s*(?P<ampm>오전|오후)\s*(?P<hour>\d{1,2}):(?P<minute>\d{2})"
)
_NOTICE_DATETIME = re.compile(
    r"(?:(?P<year>\d{4})\s*[년.-]\s*)?"
    r"(?P<month>\d{1,2})\s*월\s*(?P<day>\d{1,2})\s*일"
    r"(?:\s*\([^)]*\))?\s*(?P<ampm>오전|오후)\s*"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})"
)
_COURSE_YEAR = re.compile(r"^A(?P<year>\d{4})")


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def parse_korean_datetime(value: str) -> datetime | None:
    match = _KOREAN_DATETIME.search(normalize_text(value))
    if not match:
        return None
    hour = int(match.group("hour"))
    if match.group("ampm") == "오전":
        hour = 0 if hour == 12 else hour
    else:
        hour = hour if hour == 12 else hour + 12
    return datetime(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
        hour,
        int(match.group("minute")),
    )


def parse_notice_datetime(value: str, course_id: str) -> datetime | None:
    """Parse a notice timestamp, using the verified course year when LMS omits it."""
    match = _NOTICE_DATETIME.search(normalize_text(value))
    if not match:
        return None
    year_text = match.group("year")
    if year_text is None:
        course_match = _COURSE_YEAR.match(course_id)
        if not course_match:
            return None
        year_text = course_match.group("year")
    hour = int(match.group("hour"))
    if match.group("ampm") == "오전":
        hour = 0 if hour == 12 else hour
    else:
        hour = hour if hour == 12 else hour + 12
    try:
        return datetime(
            int(year_text),
            int(match.group("month")),
            int(match.group("day")),
            hour,
            int(match.group("minute")),
        )
    except ValueError:
        return None


def parse_courses(html: str) -> list[Course]:
    soup = BeautifulSoup(html, "html.parser")
    courses: list[Course] = []
    for anchor in soup.select('a[id^="kj_"][onclick*="eclassRoom"]'):
        match = _COURSE_ID.search(str(anchor.get("onclick", "")))
        if not match:
            continue
        course_id = match.group(1)
        if not course_id.startswith("A"):
            continue
        title = normalize_text(str(anchor.get("title", "")))
        name = title.removesuffix(" 강의실 들어가기").strip()
        text = normalize_text(anchor.get_text(" ", strip=True))
        professor_match = _PROFESSOR.search(text)
        courses.append(
            Course(
                id=course_id,
                name=name or text,
                professor=professor_match.group(1).strip() if professor_match else None,
                url=absolute(COURSE_HOME),
            )
        )
    return courses


def _direct_child_texts(node: Tag) -> list[str]:
    texts: list[str] = []
    for child in node.find_all(recursive=False):
        text = normalize_text(child.get_text(" ", strip=True))
        if text:
            texts.append(text)
    return texts


def parse_notices(html: str, course_id: str) -> list[Notice]:
    soup = BeautifulSoup(html, "html.parser")
    notices: list[Notice] = []
    for item in soup.select(".board_list_wrap[data-num]"):
        notice_id = str(item.get("data-num", "")).strip()
        text = normalize_text(item.get_text(" ", strip=True))
        title_node = item.select_one(".board_title")
        content_node = item.select_one(".board_text")
        created_node = item.select_one(
            ".board_list_bottom_right .reg_info, .board_list_bottom .reg_info, .board_list_bottom"
        )
        parts = _direct_child_texts(item)
        title = normalize_text(title_node.get_text(" ", strip=True)) if title_node else (parts[0] if parts else text)
        content = normalize_text(content_node.get_text(" ", strip=True)) if content_node else (parts[1] if len(parts) > 1 else None)
        if not notice_id:
            notice_id = stable_id(course_id, title, text)
        notices.append(
            Notice(
                id=notice_id,
                course_id=course_id,
                title=title,
                content=content,
                created_at=(
                    parse_notice_datetime(created_node.get_text(" ", strip=True), course_id)
                    if created_node
                    else None
                ),
                url=absolute(NOTICE_FORM),
            )
        )
    return notices


def enrich_notice(detail_html: str, notice: Notice) -> Notice:
    """Replace a list preview with the full notice body from the detail dialog."""
    soup = BeautifulSoup(detail_html, "html.parser")
    title_node = soup.select_one(".view_title .font_headline2, .view_title")
    content_node = soup.select_one(".editor_content")
    title = normalize_text(title_node.get_text(" ", strip=True)) if title_node else notice.title
    content = normalize_text(content_node.get_text(" ", strip=True)) if content_node else notice.content
    return Notice(
        id=notice.id,
        course_id=notice.course_id,
        title=title,
        content=content,
        created_at=notice.created_at,
        url=notice.url,
    )


def parse_assignment_index(html: str, course_id: str) -> list[Assignment]:
    soup = BeautifulSoup(html, "html.parser")
    assignments: list[Assignment] = []
    for item in soup.select('a[id^="class_menu_report_"]'):
        assignment_id = str(item.get("id", "")).removeprefix("class_menu_report_")
        title_node = item.select_one(".activity_title")
        title = normalize_text(title_node.get_text(" ", strip=True)) if title_node else normalize_text(item.get_text(" ", strip=True))
        if title.startswith("과제 "):
            title = title[3:].split(" 마감 ", 1)[0].strip()
        classes = {str(value) for value in item.get("class", [])}
        query = urlencode({"m": "report", "n": assignment_id, "mf": "report1"})
        assignments.append(
            Assignment(
                id=assignment_id,
                course_id=course_id,
                title=title,
                submitted=False if "not_submit" in classes else True,
                url=f"{absolute(ACTIVITY_FORM)}?{query}",
            )
        )
    return assignments


def enrich_assignment(detail_html: str, assignment: Assignment) -> Assignment:
    soup = BeautifulSoup(detail_html, "html.parser")
    title_node = soup.select_one(".view_title .font_headline2")
    title = normalize_text(title_node.get_text(" ", strip=True)) if title_node else assignment.title
    due_at = None
    for row in soup.select("tr"):
        text = normalize_text(row.get_text(" ", strip=True))
        if text.startswith("마감일"):
            due_at = parse_korean_datetime(text)
            break
    submit = soup.select_one("#submit_form")
    submitted = assignment.submitted
    if submit:
        submit_text = normalize_text(submit.get_text(" ", strip=True))
        if "제출된 내역이 없습니다" in submit_text:
            submitted = False
        elif "제출정보" in submit_text:
            submitted = True
    return Assignment(
        id=assignment.id,
        course_id=assignment.course_id,
        title=title,
        description=None,
        due_at=due_at,
        submitted=submitted,
        url=assignment.url,
    )


def stable_id(*parts: object) -> str:
    joined = "\x1f".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]

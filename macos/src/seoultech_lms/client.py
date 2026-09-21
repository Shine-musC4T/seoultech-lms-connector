from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from .auth import AuthenticationRequired, require_auth_state
from .endpoints import (
    ACTIVITY_LIST,
    ALLOWED_GET_PATHS,
    ALLOWED_POST_PATHS,
    BASE_URL,
    ENTER_COURSE,
    MAIN_FORM,
    NOTICE_LIST,
    NOTICE_VIEW,
    REPORT_VIEW,
)
from .models import Assignment, Course, Notice
from .parser import enrich_assignment, enrich_notice, parse_assignment_index, parse_courses, parse_notices


class ReadOnlyViolation(RuntimeError):
    pass


_BASE_PARTS = urlsplit(BASE_URL)
_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS = 5


def _allowed_paths(method: str) -> frozenset[str]:
    if method == "GET":
        return ALLOWED_GET_PATHS
    if method == "POST":
        return ALLOWED_POST_PATHS
    return frozenset()


def _validated_url(method: str, target: str) -> str:
    absolute_url = urljoin(f"{BASE_URL}/", target)
    parsed = urlsplit(absolute_url)
    same_origin = (
        parsed.scheme == "https"
        and parsed.hostname == _BASE_PARTS.hostname
        and parsed.port in (None, 443)
        and parsed.username is None
        and parsed.password is None
    )
    if not same_origin:
        raise ReadOnlyViolation(f"공식 e-Class 도메인이 아닌 요청을 차단했습니다: {absolute_url}")
    if parsed.path not in _allowed_paths(method):
        raise ReadOnlyViolation(
            f"읽기 전용 allowlist에 없는 요청을 차단했습니다: {method} {parsed.path}"
        )
    return absolute_url


def _is_login_url(target: str) -> bool:
    parsed = urlsplit(target)
    return parsed.hostname == _BASE_PARTS.hostname and "login" in parsed.path.casefold()


class SeoultechLMSClient:
    """Read-only client for the verified e-Class HTML/AJAX endpoints."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root
        self._http: httpx.AsyncClient | None = None
        self._courses_cache: list[Course] | None = None

    def _cookies(self) -> httpx.Cookies:
        state = json.loads(require_auth_state(self.project_root).read_text(encoding="utf-8"))
        cookies = httpx.Cookies()
        for cookie in state.get("cookies", []):
            domain = str(cookie.get("domain", "")).lstrip(".") or "eclass.seoultech.ac.kr"
            cookies.set(cookie["name"], cookie["value"], domain=domain, path=cookie.get("path", "/"))
        return cookies

    async def __aenter__(self) -> SeoultechLMSClient:
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            cookies=self._cookies(),
            follow_redirects=False,
            timeout=30,
            headers={
                "Accept-Language": "ko-KR,ko;q=0.9",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                ),
            },
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._http:
            await self._http.aclose()
        self._http = None

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        normalized_method = method.upper()
        target = _validated_url(normalized_method, path)
        if self._http is None:
            raise RuntimeError("SeoultechLMSClient는 'async with' 문 안에서 사용해야 합니다.")
        request_kwargs = dict(kwargs)
        for redirect_count in range(_MAX_REDIRECTS + 1):
            response = await self._http.request(normalized_method, target, **request_kwargs)
            if response.status_code in (401, 403) or _is_login_url(str(response.url)):
                raise AuthenticationRequired(
                    "LMS 로그인 세션이 만료되었습니다. start_login 도구를 호출해 로그인 창을 열어주세요. "
                    "터미널에서는 'seoultech-lms login'을 사용할 수 있습니다."
                )
            if response.status_code not in _REDIRECT_STATUS_CODES:
                _validated_url(normalized_method, str(response.url))
                response.raise_for_status()
                return response

            location = response.headers.get("location")
            if not location:
                raise RuntimeError("LMS가 목적지 없는 리다이렉트 응답을 반환했습니다.")
            redirected_target = urljoin(str(response.url), location)
            if _is_login_url(redirected_target):
                raise AuthenticationRequired(
                    "LMS 로그인 세션이 만료되었습니다. start_login 도구를 호출해 로그인 창을 열어주세요. "
                    "터미널에서는 'seoultech-lms login'을 사용할 수 있습니다."
                )
            if response.status_code == 303 or (
                response.status_code in (301, 302) and normalized_method == "POST"
            ):
                normalized_method = "GET"
                for body_key in ("content", "data", "files", "json"):
                    request_kwargs.pop(body_key, None)
            target = _validated_url(normalized_method, redirected_target)
            if redirect_count == _MAX_REDIRECTS:
                break
        raise RuntimeError("LMS 리다이렉트가 허용 횟수를 초과했습니다.")

    async def _enter_course(self, course_id: str) -> None:
        response = await self._request(
            "POST",
            ENTER_COURSE,
            data={
                "KJKEY": course_id,
                "returnData": "json",
                "returnURI": "/ilos/cls/st/submain/submain_form.acl",
                "encoding": "utf-8",
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise AuthenticationRequired(
                "강좌 세션을 열지 못했습니다. start_login 도구를 호출해 로그인 창을 열어주세요. "
                "터미널에서는 'seoultech-lms login'을 사용할 수 있습니다."
            ) from exc
        if payload.get("isError"):
            raise RuntimeError(str(payload.get("message") or "강좌 세션 진입에 실패했습니다."))

    async def get_courses(self) -> list[Course]:
        if self._courses_cache is not None:
            return list(self._courses_cache)
        response = await self._request("GET", MAIN_FORM, headers={"Accept": "text/html"})
        courses = parse_courses(response.text)
        if not courses:
            raise AuthenticationRequired("수강 과목을 찾지 못했습니다. 로그인 세션을 갱신하거나 LMS 화면 구조 변경을 확인해주세요.")
        self._courses_cache = courses
        return list(courses)

    async def get_notices(
        self,
        course_id: str | None = None,
        *,
        include_content: bool = True,
    ) -> list[Notice]:
        courses = await self.get_courses()
        selected = [course for course in courses if course.id == course_id] if course_id else courses
        if course_id and not selected:
            raise ValueError(f"수강 중인 과목 ID가 아닙니다: {course_id}")
        results: list[Notice] = []
        for course in selected:
            await self._enter_course(course.id)
            response = await self._request(
                "POST",
                NOTICE_LIST,
                data={"start": "", "display": "100", "SCH_VALUE": "", "ODR": "", "encoding": "utf-8"},
            )
            notices = parse_notices(response.text, course.id)
            if not include_content:
                results.extend(notices)
                continue
            for notice in notices:
                detail = await self._request(
                    "POST",
                    NOTICE_VIEW,
                    data={"ARTL_NUM": notice.id, "encoding": "utf-8"},
                )
                results.append(enrich_notice(detail.text, notice))
        return results

    async def get_assignments(self, course_id: str | None = None, include_completed: bool = True) -> list[Assignment]:
        courses = await self.get_courses()
        selected = [course for course in courses if course.id == course_id] if course_id else courses
        if course_id and not selected:
            raise ValueError(f"수강 중인 과목 ID가 아닙니다: {course_id}")
        results: list[Assignment] = []
        for course in selected:
            await self._enter_course(course.id)
            index_response = await self._request(
                "POST",
                ACTIVITY_LIST,
                data={"MENU_ID": "", "ARTL_NUM": "", "encoding": "utf-8"},
            )
            for assignment in parse_assignment_index(index_response.text, course.id):
                if not include_completed and assignment.submitted is True:
                    continue
                detail = await self._request(
                    "GET",
                    REPORT_VIEW,
                    params={"RT_SEQ": assignment.id, "encoding": "utf-8"},
                    headers={"Accept": "text/html"},
                )
                results.append(enrich_assignment(detail.text, assignment))
        return results

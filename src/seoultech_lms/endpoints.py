"""Endpoints verified in the authenticated SeoulTech e-Class web application."""
from __future__ import annotations

from urllib.parse import urljoin

BASE_URL = "https://eclass.seoultech.ac.kr"


def absolute(path: str) -> str:
    return urljoin(f"{BASE_URL}/", path)


# Strictly read-only allowlist. No submission, post creation, update, or delete
# endpoint belongs in this module.
MAIN_FORM = "/ilos/main/main_form.acl"
ENTER_COURSE = "/ilos/cls/st/co/eclass_room2.acl"
COURSE_HOME = "/ilos/cls/st/submain/submain_form.acl"
NOTICE_FORM = "/ilos/cls/st/notice/notice_list_form.acl"
NOTICE_LIST = "/ilos/cls/st/notice/notice_list.acl"
NOTICE_VIEW = "/ilos/cls/st/notice/notice_view_pop.acl"
ACTIVITY_FORM = "/ilos/cls/st/activity/activity_form.acl"
ACTIVITY_LIST = "/ilos/cls/st/activity/activity_list.acl"
REPORT_VIEW = "/ilos/cls/st/report/report_view_form.acl"

ALLOWED_GET_PATHS = frozenset({MAIN_FORM, COURSE_HOME, NOTICE_FORM, ACTIVITY_FORM, REPORT_VIEW})
ALLOWED_POST_PATHS = frozenset({ENTER_COURSE, NOTICE_LIST, NOTICE_VIEW, ACTIVITY_LIST})

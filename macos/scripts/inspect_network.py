"""Record only redacted Fetch/XHR metadata from an authenticated LMS session."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from playwright.async_api import Response, async_playwright

from seoultech_lms.auth import auth_state_path, require_auth_state
from seoultech_lms.browser import LMS_URL

SENSITIVE = re.compile(r"(auth|token|cookie|session|password|passwd|csrf|saml|ticket|user|student|email|phone|name)", re.I)


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    query = [(key, "[REDACTED]" if SENSITIVE.search(key) else value) for key, value in parse_qsl(parts.query, keep_blank_values=True)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key: "[REDACTED]" if SENSITIVE.search(key) else value for key, value in headers.items()}


def json_shape(value: Any, depth: int = 0) -> Any:
    if depth >= 4:
        return "…"
    if isinstance(value, dict):
        return {str(key): json_shape(item, depth + 1) for key, item in list(value.items())[:40]}
    if isinstance(value, list):
        return [json_shape(value[0], depth + 1)] if value else []
    return type(value).__name__


async def summarize(response: Response) -> dict[str, Any] | None:
    request = response.request
    if request.resource_type not in {"fetch", "xhr"}:
        return None
    content_type = response.headers.get("content-type", "")
    item: dict[str, Any] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "method": request.method,
        "url": redact_url(response.url),
        "request_headers": redact_headers(await request.all_headers()),
        "request_body": "[PRESENT: not logged]" if request.post_data else None,
        "status": response.status,
        "response_content_type": content_type,
    }
    if "json" in content_type.lower():
        try:
            item["response_json_shape"] = json_shape(await response.json())
        except Exception as exc:  # response can be unavailable or malformed
            item["response_json_shape"] = f"[unavailable: {type(exc).__name__}]"
    return item


async def run(json_only: bool) -> None:
    state = require_auth_state(ROOT)
    captured: list[dict[str, Any]] = []
    pending: set[asyncio.Task[None]] = set()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(storage_state=str(state))
        page = await context.new_page()

        async def record(response: Response) -> None:
            item = await summarize(response)
            if item and (not json_only or "json" in item["response_content_type"].lower()):
                captured.append(item)
                print(json.dumps(item, ensure_ascii=False, indent=2))

        def on_response(response: Response) -> None:
            task = asyncio.create_task(record(response))
            pending.add(task)
            task.add_done_callback(pending.discard)

        page.on("response", on_response)
        await page.goto(LMS_URL, wait_until="domcontentloaded")
        print("열린 LMS에서 메인, 수강 강좌, 과목, 공지, 과제 페이지를 직접 둘러보세요.")
        print("완료 후 이 터미널에서 Enter를 누르면 민감값을 제거한 요약만 저장하고 닫습니다.")
        input()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        await browser.close()

    output = ROOT / "data" / "network_capture.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in captured) + ("\n" if captured else ""), encoding="utf-8")
    print(f"{len(captured)}개 요청을 {output}에 저장했습니다. 이 파일은 Git에서 제외됩니다.")


parser = argparse.ArgumentParser()
parser.add_argument("--json-only", action="store_true", help="JSON 응답인 Fetch/XHR만 출력")
args = parser.parse_args()
asyncio.run(run(args.json_only))

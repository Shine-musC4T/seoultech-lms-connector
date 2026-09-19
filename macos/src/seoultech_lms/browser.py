from __future__ import annotations

import asyncio
import ctypes
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Browser, BrowserType, Error, async_playwright


LMS_URL = "https://eclass.seoultech.ac.kr/"
LOGIN_TIMEOUT_SECONDS = 10 * 60


async def _launch(browser_type: BrowserType, *, headless: bool) -> Browser:
    """Prefer the installed Chrome channel; fall back to bundled Chromium."""
    try:
        return await browser_type.launch(channel="chrome", headless=headless)
    except Error:
        return await browser_type.launch(headless=headless)


def _is_authenticated_lms_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.casefold()
    return (
        parsed.hostname == "eclass.seoultech.ac.kr"
        and "/ilos/main/" in path
        and "login" not in path
    )


async def interactive_login(
    state_path: Path,
    *,
    wait_for_enter: bool = True,
    timeout_seconds: int = LOGIN_TIMEOUT_SECONDS,
) -> None:
    """Open LMS; the user completes any authentication personally in Chromium."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await _launch(playwright.chromium, headless=False)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(LMS_URL, wait_until="domcontentloaded")
            if wait_for_enter:
                print("브라우저에서 직접 로그인한 뒤 LMS 메인 화면이 보이면 여기 터미널에서 Enter를 누르세요.")
                input()
            else:
                deadline = asyncio.get_running_loop().time() + timeout_seconds
                while not _is_authenticated_lms_url(page.url):
                    if page.is_closed():
                        raise RuntimeError("로그인 창이 완료 전에 닫혔습니다.")
                    if asyncio.get_running_loop().time() >= deadline:
                        raise TimeoutError("LMS 로그인 대기 시간이 만료되었습니다.")
                    await page.wait_for_timeout(500)
                await page.wait_for_timeout(1000)
            await context.storage_state(path=str(state_path))
        finally:
            await browser.close()


def _process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
            process_query_limited_information,
            False,
            pid,
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
        return True
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def start_login_browser(state_path: Path) -> dict[str, str]:
    """Start a detached login helper so MCP stdio remains available."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path = state_path.with_name("login_process.pid")
    try:
        existing_pid = int(pid_path.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        existing_pid = 0
    if _process_is_running(existing_pid):
        return {
            "status": "already_open",
            "message": "이미 LMS 로그인 창이 열려 있습니다. 열린 창에서 직접 로그인해주세요.",
        }

    popen_options: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        popen_options["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        popen_options["start_new_session"] = True

    process = subprocess.Popen(  # noqa: S603 - fixed local module invocation
        [sys.executable, "-m", "seoultech_lms.login_window"],
        **popen_options,
    )
    pid_path.write_text(str(process.pid), encoding="utf-8")
    return {
        "status": "started",
        "message": (
            "LMS 로그인용 Chrome 창을 열었습니다. 브라우저에서 직접 로그인하세요. "
            "LMS 메인 화면이 확인되면 세션이 저장되고 창이 자동으로 닫힙니다."
        ),
    }


async def session_is_valid(state_path: Path) -> bool:
    """Conservative check: an expired state must be renewed interactively."""
    if not state_path.is_file():
        return False
    async with async_playwright() as playwright:
        browser = await _launch(playwright.chromium, headless=True)
        context = await browser.new_context(storage_state=str(state_path))
        page = await context.new_page()
        try:
            response = await page.goto(LMS_URL, wait_until="domcontentloaded")
            valid = bool(response and response.ok and "login" not in page.url.lower())
        finally:
            await browser.close()
    return valid

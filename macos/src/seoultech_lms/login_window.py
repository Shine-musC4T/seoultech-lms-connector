from __future__ import annotations

import asyncio
import os

from .auth import auth_state_path
from .browser import interactive_login


def main() -> None:
    state_path = auth_state_path()
    pid_path = state_path.with_name("login_process.pid")
    try:
        asyncio.run(interactive_login(state_path, wait_for_enter=False))
    finally:
        try:
            recorded_pid = int(pid_path.read_text(encoding="utf-8").strip())
            if recorded_pid == os.getpid():
                pid_path.unlink(missing_ok=True)
        except (FileNotFoundError, ValueError):
            pass


if __name__ == "__main__":
    main()

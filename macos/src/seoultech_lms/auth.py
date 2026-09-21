from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


class AuthenticationRequired(RuntimeError):
    """Raised when the locally saved browser session is absent or expired."""


def user_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "seoultech-lms-connector"
    if local_app_data := os.environ.get("LOCALAPPDATA"):
        return Path(local_app_data) / "seoultech-lms-connector"
    if xdg_data_home := os.environ.get("XDG_DATA_HOME"):
        return Path(xdg_data_home) / "seoultech-lms-connector"
    return Path.home() / ".local" / "share" / "seoultech-lms-connector"


def auth_state_path(project_root: Path | None = None) -> Path:
    return (project_root / "data" if project_root else user_data_dir()) / "auth_state.json"


def ensure_private_directory(path: Path) -> None:
    """Create a user-only directory on POSIX without weakening other platforms."""
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        path.chmod(0o700)


def harden_auth_state(path: Path) -> None:
    """Restrict an existing authentication state file to its owner on POSIX."""
    if os.name == "posix" and path.is_file():
        path.chmod(0o600)


def write_auth_state_secure(path: Path, state: dict[str, Any]) -> None:
    """Atomically persist browser state with user-only POSIX permissions."""
    ensure_private_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        harden_auth_state(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def require_auth_state(project_root: Path | None = None) -> Path:
    path = auth_state_path(project_root)
    if not path.is_file():
        raise AuthenticationRequired(
            "LMS 로그인 세션이 없습니다. start_login 도구를 호출해 로그인 창을 열어주세요. "
            "터미널에서는 'seoultech-lms login'을 사용할 수 있습니다."
        )
    harden_auth_state(path)
    return path

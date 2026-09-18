from __future__ import annotations

import os
from pathlib import Path


class AuthenticationRequired(RuntimeError):
    """Raised when the locally saved browser session is absent or expired."""


def user_data_dir() -> Path:
    if local_app_data := os.environ.get("LOCALAPPDATA"):
        return Path(local_app_data) / "seoultech-lms-connector"
    if xdg_data_home := os.environ.get("XDG_DATA_HOME"):
        return Path(xdg_data_home) / "seoultech-lms-connector"
    return Path.home() / ".local" / "share" / "seoultech-lms-connector"


def auth_state_path(project_root: Path | None = None) -> Path:
    return (project_root / "data" if project_root else user_data_dir()) / "auth_state.json"


def require_auth_state(project_root: Path | None = None) -> Path:
    path = auth_state_path(project_root)
    if not path.is_file():
        raise AuthenticationRequired(
            "LMS 로그인 세션이 없습니다. start_login 도구를 호출해 로그인 창을 열어주세요. "
            "터미널에서는 'seoultech-lms login'을 사용할 수 있습니다."
        )
    return path

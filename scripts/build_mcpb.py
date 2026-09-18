from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


TOOLS = [
    ("start_login", "로그인 세션이 없거나 만료됐을 때 사용자가 직접 로그인할 Chrome 창을 연다."),
    ("list_courses", "현재 수강 중인 과목 목록을 조회한다."),
    ("list_notices", "전체 과목 또는 지정한 과목의 공지 목록, 게시일과 전체 본문을 조회한다."),
    ("search_notices", "공지 전체 본문에서 검색하고 각 결과의 게시일도 함께 반환한다."),
    ("list_assignments", "전체 과목 또는 지정한 과목의 과제와 제출 상태를 조회한다."),
    ("get_pending_assignments", "현재 미제출 과제를 마감일 순으로 조회한다."),
    ("get_upcoming_deadlines", "지정한 기간 안에 마감되는 미제출 과제를 조회한다."),
]


def build_mcpb(
    project_root: Path,
    output_path: Path,
    python_executable: str,
    version: str,
) -> Path:
    icon_path = project_root / "plugin" / "seoultech-c4t" / "assets" / "icon.png"
    entry_point = project_root / "claude-extension" / "server" / "main.py"
    if not icon_path.is_file():
        raise FileNotFoundError(f"Claude extension icon not found: {icon_path}")
    if not entry_point.is_file():
        raise FileNotFoundError(f"Claude extension entry point not found: {entry_point}")

    manifest = {
        "manifest_version": "0.3",
        "name": "seoultech-c4t",
        "display_name": "seoultech_c4t",
        "version": version,
        "description": "서울과기대 e-Class 공지와 과제를 읽기 전용으로 확인합니다.",
        "long_description": (
            "서울과학기술대학교 e-Class에서 수강 과목, 공지 본문, 과제, "
            "제출 여부와 마감일을 읽기 전용으로 조회합니다."
        ),
        "author": {"name": "C4T"},
        "icon": "icon.png",
        "icons": [{"src": "icon.png", "size": "512x512"}],
        "server": {
            "type": "python",
            "entry_point": "server/main.py",
            "mcp_config": {
                "command": python_executable,
                "args": ["${__dirname}/server/main.py"],
                "env": {"PYTHONUTF8": "1"},
            },
        },
        "tools": [
            {"name": name, "description": description}
            for name, description in TOOLS
        ],
        "tools_generated": False,
        "keywords": ["seoultech", "e-class", "lms", "assignments", "notices"],
        "compatibility": {
            "claude_desktop": ">=1.0.0",
            "platforms": ["win32"],
            "runtimes": {"python": ">=3.12"},
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        bundle.writestr("manifest.json", manifest_bytes)
        bundle.write(icon_path, "icon.png")
        bundle.write(entry_point, "server/main.py")
    temporary.replace(output_path)
    return output_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the Claude Desktop MCPB extension")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--version", required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = build_mcpb(
        args.project_root.resolve(),
        args.output.resolve(),
        args.python_executable,
        args.version,
    )
    print(result)


if __name__ == "__main__":
    main()

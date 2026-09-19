#!/bin/bash

set -Eeuo pipefail
IFS=$'\n\t'

REMOVE_AUTH=0

usage() {
    cat <<'EOF'
사용법: bash uninstall.sh [옵션]

  --remove-auth  저장된 LMS 로그인 세션도 함께 삭제합니다.
  -h, --help     도움말을 표시합니다.
EOF
}

while (($#)); do
    case "$1" in
        --remove-auth) REMOVE_AUTH=1 ;;
        -h|--help) usage; exit 0 ;;
        *) printf '알 수 없는 옵션: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

if [[ "$(uname -s)" != "Darwin" ]]; then
    printf '이 제거 파일은 macOS 전용입니다.\n' >&2
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
APP_SUPPORT_DIR="$HOME/Library/Application Support/seoultech-lms-connector"
VENV_DIR="$APP_SUPPORT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
SETUP_SCRIPT="$SCRIPT_DIR/scripts/setup_integrations.py"
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

if [[ -x "$VENV_PYTHON" ]]; then
    remove_json="$("$VENV_PYTHON" "$SETUP_SCRIPT" uninstall \
        --user-profile "$HOME" \
        --claude-config "$CLAUDE_CONFIG")"
    marketplace_name="$(printf '%s' "$remove_json" | "$VENV_PYTHON" -c 'import json,sys; print(json.load(sys.stdin).get("marketplace_name", "personal"))')"
else
    printf '설치된 전용 Python 환경이 없어 설정 파일 자동 정리를 진행할 수 없습니다.\n' >&2
    printf '먼저 같은 버전의 install.sh를 실행한 뒤 다시 제거하거나, README의 수동 제거 절차를 확인하세요.\n' >&2
    exit 1
fi

if command -v codex >/dev/null 2>&1; then
    codex plugin remove "seoultech-c4t@$marketplace_name" >/dev/null 2>&1 || true
fi

if command -v claude >/dev/null 2>&1; then
    claude mcp remove seoultech_c4t --scope user >/dev/null 2>&1 || true
fi

rm -f -- "$APP_SUPPORT_DIR/seoultech-c4t.mcpb"

case "$VENV_DIR" in
    "$HOME/Library/Application Support/seoultech-lms-connector/venv")
        rm -rf -- "$VENV_DIR"
        ;;
    *)
        printf '예상하지 못한 가상환경 경로라 삭제를 중단합니다: %s\n' "$VENV_DIR" >&2
        exit 1
        ;;
esac

if ((REMOVE_AUTH)); then
    rm -f -- "$APP_SUPPORT_DIR/auth_state.json" "$APP_SUPPORT_DIR/login_process.pid"
    printf '저장된 LMS 로그인 세션도 삭제했습니다.\n'
fi

rmdir "$APP_SUPPORT_DIR" 2>/dev/null || true

cat <<'EOF'
제거 완료. 로그인 세션은 --remove-auth를 지정한 경우에만 삭제했습니다.
Claude Desktop에 별도로 설치한 seoultech_c4t 확장은 Settings > Extensions에서 제거하세요.
Codex와 Claude를 완전히 종료한 뒤 다시 실행하세요.
EOF

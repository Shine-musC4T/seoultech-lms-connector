#!/bin/bash

set -Eeuo pipefail
IFS=$'\n\t'

SKIP_CODEX=0
SKIP_CLAUDE=0
SKIP_LOGIN=0

usage() {
    cat <<'EOF'
사용법: bash install.sh [옵션]

  --skip-codex   Codex 플러그인 설정을 건너뜁니다.
  --skip-claude  Claude Desktop/Claude Code 설정을 건너뜁니다.
  --skip-login   최초 LMS 로그인을 건너뜁니다.
  -h, --help     도움말을 표시합니다.
EOF
}

while (($#)); do
    case "$1" in
        --skip-codex) SKIP_CODEX=1 ;;
        --skip-claude) SKIP_CLAUDE=1 ;;
        --skip-login) SKIP_LOGIN=1 ;;
        -h|--help) usage; exit 0 ;;
        *) printf '알 수 없는 옵션: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

if [[ "$(uname -s)" != "Darwin" ]]; then
    printf '이 설치 파일은 macOS 전용입니다.\n' >&2
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
PROJECT_ROOT="$SCRIPT_DIR"
APP_SUPPORT_DIR="$HOME/Library/Application Support/seoultech-lms-connector"
VENV_DIR="$APP_SUPPORT_DIR/venv"
PLUGIN_SOURCE="$PROJECT_ROOT/plugin/seoultech-c4t"
SETUP_SCRIPT="$PROJECT_ROOT/scripts/setup_integrations.py"
BUILD_MCPB_SCRIPT="$PROJECT_ROOT/scripts/build_mcpb.py"
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

find_python_312() {
    local candidate resolved version
    for candidate in "${PYTHON312:-}" python3.12 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
        [[ -n "$candidate" ]] || continue
        if resolved="$(command -v "$candidate" 2>/dev/null)"; then
            :
        elif [[ -x "$candidate" ]]; then
            resolved="$candidate"
        else
            continue
        fi
        version="$("$resolved" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
        if [[ "$version" == "3.12" ]]; then
            printf '%s\n' "$resolved"
            return 0
        fi
    done
    return 1
}

if ! PYTHON_EXE="$(find_python_312)"; then
    cat >&2 <<'EOF'
Python 3.12를 찾지 못했습니다.

Homebrew가 있다면 아래 명령으로 설치한 뒤 이 설치 파일을 다시 실행하세요.
  brew install python@3.12

Homebrew가 없다면 https://www.python.org/downloads/macos/ 에서
Python 3.12 macOS 설치 파일을 받아 설치해도 됩니다.
EOF
    exit 1
fi

mkdir -p "$APP_SUPPORT_DIR"

printf '[1/7] macOS 전용 Python 가상환경을 준비합니다.\n'
"$PYTHON_EXE" -m venv "$VENV_DIR"
VENV_PYTHON="$VENV_DIR/bin/python3"
"$VENV_PYTHON" -m pip install --disable-pip-version-check --upgrade pip setuptools
"$VENV_PYTHON" -m pip install --disable-pip-version-check --upgrade "$PROJECT_ROOT"

if [[ ! -d "/Applications/Google Chrome.app" && ! -d "$HOME/Applications/Google Chrome.app" ]]; then
    printf '[2/7] Chrome이 없어 로그인용 Chromium을 설치합니다.\n'
    "$VENV_PYTHON" -m playwright install chromium
else
    printf '[2/7] 설치된 Google Chrome을 사용합니다.\n'
fi

setup_args=(
    "$SETUP_SCRIPT" install
    --plugin-source "$PLUGIN_SOURCE"
    --user-profile "$HOME"
    --python-executable "$VENV_PYTHON"
    --claude-config "$CLAUDE_CONFIG"
)
((SKIP_CODEX)) && setup_args+=(--skip-codex)
((SKIP_CLAUDE)) && setup_args+=(--skip-claude-desktop)

integration_json="$("$VENV_PYTHON" "${setup_args[@]}")"
marketplace_name="$(printf '%s' "$integration_json" | "$VENV_PYTHON" -c 'import json,sys; print(json.load(sys.stdin).get("marketplace_name", "personal"))')"

if ((SKIP_CODEX)); then
    printf '[3/7] Codex 설정을 건너뜁니다.\n'
else
    printf '[3/7] Codex 개인 플러그인과 마켓플레이스를 설정했습니다.\n'
    if command -v codex >/dev/null 2>&1; then
        if codex plugin add "seoultech-c4t@$marketplace_name"; then
            printf '      Codex 플러그인 등록까지 완료했습니다.\n'
        else
            printf '      Codex CLI 등록은 지원 버전 차이로 건너뜁니다. 앱을 재시작한 뒤 플러그인 목록에서 설치하세요.\n' >&2
        fi
    else
        printf '      Codex CLI가 PATH에 없어 앱 재시작 후 플러그인 목록에서 설치하면 됩니다.\n'
    fi
fi

if ((SKIP_CLAUDE)); then
    printf '[4/7] Claude Desktop 설정을 건너뜁니다.\n'
    printf '[5/7] Claude Desktop 확장 빌드를 건너뜁니다.\n'
    printf '[6/7] Claude Code 설정을 건너뜁니다.\n'
else
    printf '[4/7] Claude Desktop의 기본 로컬 MCP 연결을 설정했습니다.\n'
    manifest_path="$PLUGIN_SOURCE/.codex-plugin/plugin.json"
    plugin_version="$("$VENV_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$manifest_path")"
    claude_bundle="$APP_SUPPORT_DIR/seoultech-c4t.mcpb"
    "$VENV_PYTHON" "$BUILD_MCPB_SCRIPT" \
        --project-root "$PROJECT_ROOT" \
        --output "$claude_bundle" \
        --python-executable "$VENV_PYTHON" \
        --version "$plugin_version" >/dev/null
    printf '[5/7] Claude Desktop 확장 파일을 만들었습니다.\n'
    printf '      Claude Desktop > Settings > Extensions > Advanced settings > Install Extension에서\n'
    printf '      다음 파일을 선택하세요: %s\n' "$claude_bundle"

    if command -v claude >/dev/null 2>&1; then
        claude mcp remove seoultech_c4t --scope user >/dev/null 2>&1 || true
        claude_server_json="$("$VENV_PYTHON" -c 'import json,sys; print(json.dumps({"type":"stdio","command":sys.argv[1],"args":["-m","seoultech_lms.mcp_server"],"env":{}}))' "$VENV_PYTHON")"
        claude mcp add-json seoultech_c4t "$claude_server_json" --scope user
        printf '[6/7] Claude Code MCP 서버를 등록했습니다.\n'
    else
        printf '[6/7] Claude Code가 없어 CLI 등록만 건너뜁니다. Claude Desktop 연결은 준비됐습니다.\n'
    fi
fi

AUTH_PATH="$APP_SUPPORT_DIR/auth_state.json"
if ((SKIP_LOGIN)); then
    printf '[7/7] LMS 로그인을 건너뜁니다. 나중에 아래 명령으로 로그인하세요.\n'
    printf '      "%s" -m seoultech_lms.cli login\n' "$VENV_PYTHON"
elif [[ -f "$AUTH_PATH" ]]; then
    printf '[7/7] 기존 LMS 로그인 세션을 유지합니다.\n'
else
    printf '[7/7] 최초 LMS 로그인을 시작합니다. 브라우저에서 직접 로그인하세요.\n'
    "$VENV_PYTHON" -m seoultech_lms.cli login
fi

cat <<EOF

설치 완료.
- 앱 데이터: $APP_SUPPORT_DIR
- Python 실행 파일: $VENV_PYTHON
- 로그인 세션은 이 Mac 안에만 저장됩니다.

Codex와 Claude를 완전히 종료한 뒤 다시 실행하세요.
EOF

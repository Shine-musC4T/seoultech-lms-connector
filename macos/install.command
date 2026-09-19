#!/bin/bash

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd -P)"
/bin/bash "$SCRIPT_DIR/install.sh" "$@"
status=$?
printf '\n완료 화면을 닫으려면 Enter를 누르세요. '
read -r _
exit "$status"

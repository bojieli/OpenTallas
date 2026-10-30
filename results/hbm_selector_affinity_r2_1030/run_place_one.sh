#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/codex-hbm-selector-1030/roles_fresh
K=$1
python3 "$K/check_logic_reuse.py" "$K"
set +e
bash "$R/run_kit_qualified.sh" "$K" place 40 16 > "$K/run_place.log" 2>&1
rc=$?
set -e
echo "$rc" > "$K/place.rc"
tail -12 "$K/run_place.log"
exit "$rc"

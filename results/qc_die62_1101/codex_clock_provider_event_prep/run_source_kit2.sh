#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc62-clock-frozen-source-1102
T=/srv/opentallas-scratch2/claude/wt/codex-qc62-bind-complete-1101
cd "$T"
python3 tools/clk/ot_clk.py check "$R/config.yaml" > "$R/check2.remote.log" 2>&1 || exit $?
python3 tools/clk/ot_clk.py kit "$R/config.yaml" --out "$R/emitted2" --workers 2 > "$R/source_kit2.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$R/source_kit2.rc"
exit "$rc"

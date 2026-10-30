#!/usr/bin/env bash
set -u
R=/srv/opentallas-scratch2/claude/codex-hbm-bind-1848
W=/srv/opentallas-scratch2/claude/wt/codex-hbm-bind-1848
python3 "$W/tools/die_plan/bind.py" bind /srv/opentallas-scratch2/claude/die-hbm-24/plan/d23c/die_plan.json --asbuilt "$R/d23c_b1/asbuilt.json" --out "$R/d23c_b1/out" --strict --mem 24 > "$R/d23c_b1/bind.log" 2>&1
rc=$?
echo "$rc" > "$R/d23c_b1/bind.rc"
exit "$rc"

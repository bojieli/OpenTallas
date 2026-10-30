#!/usr/bin/env bash
set -u
R=/srv/opentallas-scratch2/claude/codex-hbm-bind-2249
W=/srv/opentallas-scratch2/claude/wt/codex-hbm-bind-2249
python3 "$W/tools/die_plan/bind.py" bind /srv/opentallas-scratch2/claude/die-hbm-29/plan/d29d/die_plan.json --asbuilt "$R/row1/manifest.json" --out "$R/row1_bind/out" --strict --all-gaps --mem 24 > "$R/row1_bind/bind.log" 2>&1
rc=$?; echo "$rc" > "$R/row1_bind/bind.rc";exit "$rc"

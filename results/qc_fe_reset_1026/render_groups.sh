#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-fe-reset-1026
mkdir -p "$R/geometry"
for t in slw_fe_v1 sle_fe_v1 sle_fe_v2 sle_fe_v3; do
 if python3 "$R/fup_reset_groups.py" --conn "$R/conn_$t.tsv" --type "$t" --out "$R/geometry/$t" --png > "$R/geometry/$t.log" 2>&1; then cat "$R/geometry/$t.log"; else echo "$t BLOCKED master/group inspection: $R/geometry/$t.log"; fi
done

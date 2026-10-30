#!/bin/bash
set -u
R=/srv/opentallas-scratch2/claude/die-qc-49/collft
W=/srv/opentallas-scratch2/claude/wt/die-qc-49-collft
cd "$W"
python3 tools/clk/ot_clk.py check "$R/gen50/config.yaml" > "$R/gen50/check.log" 2>&1 || { echo "rc=check_fail $(date -Is)" > "$R/gen50/status"; exit 3; }
/usr/bin/time -v python3 tools/clk/ot_clk.py kit "$R/gen50/config.yaml" --out "$R/gen50/out" --workers 24 > "$R/gen50/kit.log" 2> "$R/gen50/kit.time"
rc=$?
echo "rc=$rc $(date -Is)" > "$R/gen50/status"
exit $rc

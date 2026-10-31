#!/bin/bash
set -u
R=/srv/opentallas-scratch2/claude/die-qc-51
cd /srv/opentallas-scratch2/claude/wt/die-qc-51
python3 tools/clk/ot_clk.py check "$R/gen52/config.yaml" > "$R/gen52/check.log" 2>&1 || { echo "rc=check_fail $(date -Is)" > "$R/gen52/status"; exit 3; }
/usr/bin/time -v python3 tools/clk/ot_clk.py kit "$R/gen52/config.yaml" --out "$R/gen52/out" --workers 24 > "$R/gen52/kit.log" 2> "$R/gen52/kit.time"
rc=$?
echo "rc=$rc $(date -Is)" > "$R/gen52/status"
exit $rc
